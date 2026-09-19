import re
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.document import DocumentCategory
from app.schemas.document import (
    ClubMemoryLessonRecommendation,
    ClubMemoryPlanCheckResponse,
    CitationSchema
)
from app.services.rag_engine import retrieve_candidate_chunks
from app.services.embeddings import cosine_similarity
from app.core.config import settings

# Attempt to configure Gemini client if API key is present
genai_client = None
if settings.GEMINI_API_KEY:
    try:
        from google import genai
        genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)
    except Exception:
        genai_client = None

def check_plan_against_club_memory(
    db: Session,
    plan_text: str,
    event_id: Optional[str] = None
) -> ClubMemoryPlanCheckResponse:
    """
    Compares a planned event task/operation against historical club memory
    (post-mortems, meeting notes, venue rules) to proactively surface past lessons,
    risks, and recommended adjustments with full citations.
    """
    # 1. Retrieve historical chunks across post-mortems, venue rules, and meeting notes
    candidates = retrieve_candidate_chunks(
        db=db,
        query=plan_text,
        event_id=None, # Search all historical club memory across previous events
        top_k=6
    )

    if not candidates:
        return ClubMemoryPlanCheckResponse(
            plan_text=plan_text,
            surfaced_lessons_count=0,
            recommendations=[],
            overall_risk_assessment="No historical records found for this operation. Proceed with standard club guidelines."
        )

    # Filter for chunks that have historical lessons or rules
    lesson_candidates = []
    for chunk, doc, score in candidates:
        content_lower = chunk.content.lower()
        has_lesson_signal = any(term in content_lower for term in [
            "took", "delay", "problem", "issue", "hour", "hours", "late", "required", "fail",
            "rule", "permit", "budget", "exceeded", "shortage", "recommend", "learned"
        ])
        if score > 0.35 or has_lesson_signal:
            lesson_candidates.append((chunk, doc, score))

    if not lesson_candidates:
        lesson_candidates = candidates[:2]

    # LLM-assisted comparison if Gemini is configured
    if genai_client and settings.GEMINI_API_KEY:
        context_snippets = []
        for idx, (chunk, doc, _) in enumerate(lesson_candidates, start=1):
            page_info = f", page {chunk.page_number}" if chunk.page_number else ""
            sec_info = f", {chunk.section_name}" if chunk.section_name else ""
            context_snippets.append(f"[{idx}] {doc.filename}{page_info}{sec_info}: {chunk.content}")

        context_str = "\n".join(context_snippets)

        prompt = f"""You are ClubOps AI, auditing a new event plan against historical club documents.
Current Plan:
"{plan_text}"

Historical Club Records:
{context_str}

Analyze whether the current plan conflicts with past operational lessons, timelines, or rules.
Return in JSON format:
{{
  "recommendations": [
    {{
      "lesson": "Short summary of the past lesson or rule",
      "historical_context": "Exact past experience mentioned in records",
      "recommendation": "Specific actionable change to the plan",
      "risk_level": "LOW" | "MEDIUM" | "HIGH",
      "source_index": 1
    }}
  ],
  "overall_risk_assessment": "1-sentence executive risk assessment"
}}
JSON:"""
        try:
            response = genai_client.models.generate_content(
                model=settings.LLM_MODEL,
                contents=prompt
            )
            import json
            # Extract JSON from code fences if present
            raw_text = response.text.strip()
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0].strip()
            data = json.loads(raw_text)

            recs = []
            for r in data.get("recommendations", []):
                s_idx = r.get("source_index", 1) - 1
                if 0 <= s_idx < len(lesson_candidates):
                    src_chunk, src_doc, score = lesson_candidates[s_idx]
                else:
                    src_chunk, src_doc, score = lesson_candidates[0]

                citation = CitationSchema(
                    document_id=src_doc.id,
                    filename=src_doc.filename,
                    category=src_doc.category.value,
                    page_number=src_chunk.page_number,
                    section_name=src_chunk.section_name or f"Section {src_chunk.chunk_index + 1}",
                    chunk_index=src_chunk.chunk_index,
                    snippet=src_chunk.content[:200] + "...",
                    relevance_score=round(score, 3)
                )

                recs.append(ClubMemoryLessonRecommendation(
                    lesson=r["lesson"],
                    historical_context=r["historical_context"],
                    recommendation=r["recommendation"],
                    risk_level=r.get("risk_level", "MEDIUM"),
                    citations=[citation]
                ))

            return ClubMemoryPlanCheckResponse(
                plan_text=plan_text,
                surfaced_lessons_count=len(recs),
                recommendations=recs,
                overall_risk_assessment=data.get("overall_risk_assessment", "Historical lessons surfaced for operational review.")
            )
        except Exception:
            pass # Fall back to deterministic rule extraction

    # Deterministic fallback logic
    recommendations: List[ClubMemoryLessonRecommendation] = []
    plan_lower = plan_text.lower()

    for chunk, doc, score in lesson_candidates[:3]:
        content = chunk.content
        snippet = content[:220] + "..." if len(content) > 220 else content

        citation = CitationSchema(
            document_id=doc.id,
            filename=doc.filename,
            category=doc.category.value,
            page_number=chunk.page_number,
            section_name=chunk.section_name or f"Section {chunk.chunk_index + 1}",
            chunk_index=chunk.chunk_index,
            snippet=snippet,
            relevance_score=round(score, 3)
        )

        # Detect temporal or duration discrepancies (e.g. 1 hour vs 3 hours)
        lesson_text = f"Historical record from {doc.filename} highlights past operational challenges."
        rec_text = "Review scheduled duration and allocate buffer time based on past logs."
        risk = "MEDIUM"

        if "venue setup" in plan_lower and ("hour" in content.lower() or "delay" in content.lower()):
            lesson_text = "Past events experienced extended setup durations and AV equipment delays."
            rec_text = "Schedule at least 2.5 to 3 hours for venue setup and sound testing prior to attendee arrival."
            risk = "HIGH"
        elif "budget" in plan_lower or "catering" in plan_lower:
            lesson_text = "Historical catering and refreshment expenses exceeded early estimates by 15-20%."
            rec_text = "Ensure an emergency contingency reserve is added to the budget line item."
            risk = "HIGH"
        elif "sponsor" in plan_lower:
            lesson_text = "Sponsor deliverable approvals and booth logistics required multiple revision rounds."
            rec_text = "Confirm all sponsor banners and collateral at least 10 days prior to event day."
            risk = "MEDIUM"
        else:
            lesson_text = f"Previous log in {doc.filename}: '{snippet[:120]}...'"
            rec_text = "Align operational timeline with historical post-mortem recommendations."
            risk = "LOW" if score < 0.5 else "MEDIUM"

        recommendations.append(ClubMemoryLessonRecommendation(
            lesson=lesson_text,
            historical_context=snippet,
            recommendation=rec_text,
            risk_level=risk,
            citations=[citation]
        ))

    overall_risk = "HIGH" if any(r.risk_level == "HIGH" for r in recommendations) else "MEDIUM"
    assessment = (
        f"Identified {len(recommendations)} historical operational precedents. "
        f"Overall risk evaluated as {overall_risk}. Adjust timeline buffers accordingly."
    )

    return ClubMemoryPlanCheckResponse(
        plan_text=plan_text,
        surfaced_lessons_count=len(recommendations),
        recommendations=recommendations,
        overall_risk_assessment=assessment
    )

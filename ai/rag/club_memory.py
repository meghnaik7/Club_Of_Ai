import re
import json
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.document import DocumentCategory
from app.schemas.document import (
    ClubMemoryLessonRecommendation,
    ClubMemoryPlanCheckResponse,
    CitationSchema
)
from ai.rag.retrieval import retrieve_candidate_chunks
from ai.rag.reranker import rerank_chunks
from ai.rag.crag_grader import grade_retrieved_documents_crag
from ai.rag.self_rag import build_citations
from app.core.config import settings

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
    Compares a planned event task or schedule against historical club memory
    (post-mortems, meeting notes, venue rules) to proactively surface past lessons,
    bottlenecks, and recommended adjustments with full citations.
    """
    if not plan_text or not plan_text.strip():
        return ClubMemoryPlanCheckResponse(
            plan_text=plan_text,
            surfaced_lessons_count=0,
            recommendations=[],
            overall_risk_assessment="Plan text is empty. Provide an event plan or task schedule to audit."
        )

    # 1. Retrieve candidates across historical documents (all events or past events)
    candidates = retrieve_candidate_chunks(
        db=db,
        query=plan_text,
        event_id=None,
        candidate_k=15
    )

    if not candidates:
        return ClubMemoryPlanCheckResponse(
            plan_text=plan_text,
            surfaced_lessons_count=0,
            recommendations=[],
            overall_risk_assessment="No historical club records found for this operation. Proceed with standard club guidelines."
        )

    # 2. Re-rank
    reranked = rerank_chunks(plan_text, candidates, top_k=8)

    # 3. Filter for historical lessons, delays, rules, or post-mortem notes
    lesson_candidates = []
    lesson_keywords = [
        "took", "delay", "problem", "issue", "hour", "hours", "late", "required", "fail",
        "rule", "permit", "budget", "exceeded", "shortage", "recommend", "learned", "bottleneck"
    ]

    for chunk, doc, score in reranked:
        content_lower = chunk.content.lower()
        has_signal = any(k in content_lower for k in lesson_keywords)
        is_post_mortem = (doc.category == DocumentCategory.POST_MORTEM) if hasattr(doc, "category") else False

        if score >= 0.25 or has_signal or is_post_mortem:
            lesson_candidates.append((chunk, doc, score))

    if not lesson_candidates:
        lesson_candidates = reranked[:2]

    # 4. CRAG Relevance Grader
    relevant_chunks, _ = grade_retrieved_documents_crag(plan_text, lesson_candidates, threshold=0.20)
    if not relevant_chunks:
        relevant_chunks = lesson_candidates[:2]

    # Build citations
    citations = build_citations(relevant_chunks)

    # 5. LLM Analysis if Gemini API is available
    if genai_client and settings.GEMINI_API_KEY:
        context_snippets = []
        for idx, (chunk, doc, _) in enumerate(relevant_chunks, start=1):
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
            if response and response.text:
                json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(0))
                    recommendations = []
                    for r in data.get("recommendations", []):
                        src_idx = max(0, min(len(citations) - 1, r.get("source_index", 1) - 1))
                        recommendations.append(ClubMemoryLessonRecommendation(
                            lesson=r.get("lesson", "Past operational lesson"),
                            historical_context=r.get("historical_context", ""),
                            recommendation=r.get("recommendation", "Review schedule with experienced lead."),
                            risk_level=r.get("risk_level", "MEDIUM"),
                            citations=[citations[src_idx]] if citations else []
                        ))
                    return ClubMemoryPlanCheckResponse(
                        plan_text=plan_text,
                        surfaced_lessons_count=len(recommendations),
                        recommendations=recommendations,
                        overall_risk_assessment=data.get("overall_risk_assessment", "Potential conflicts with past lessons detected.")
                    )
        except Exception:
            pass

    # 6. Offline / Local Heuristic Rule-Based Auditing
    recommendations = []
    plan_lower = plan_text.lower()

    # Rule A: Setup time conflict detection
    if any(k in plan_lower for k in ["setup", "set up", "stage", "venue", "audio", "sound"]):
        for idx, (chunk, doc, _) in enumerate(relevant_chunks):
            content_lower = chunk.content.lower()
            if "hour" in content_lower and ("took" in content_lower or "require" in content_lower or "delay" in content_lower):
                # Extract sentence
                sentences = [s for s in chunk.content.split(".") if any(w in s.lower() for w in ["took", "hour", "delay", "setup"])]
                snippet_text = sentences[0].strip() if sentences else chunk.content[:150]
                rec = ClubMemoryLessonRecommendation(
                    lesson="Venue setup frequently takes longer than 1-2 hours due to equipment and distribution requirements.",
                    historical_context=snippet_text,
                    recommendation="Allocate at least 3 hours prior to attendee entry for setup and sound checks.",
                    risk_level="HIGH" if ("1 hour" in plan_lower or "1hr" in plan_lower or "short" in plan_lower) else "MEDIUM",
                    citations=[citations[idx]] if idx < len(citations) else []
                )
                recommendations.append(rec)
                break

    # Rule B: Sponsor or Registration bottleneck detection
    if any(k in plan_lower for k in ["sponsor", "registration", "desk", "check-in"]):
        for idx, (chunk, doc, _) in enumerate(relevant_chunks):
            content_lower = chunk.content.lower()
            if "sponsor" in content_lower or "registration" in content_lower:
                rec = ClubMemoryLessonRecommendation(
                    lesson="Registration desk was bottlenecked during previous events.",
                    historical_context="Sponsor coordination had critical delays at the registration desk and booth assignments.",
                    recommendation="Set up a dedicated fast-track registration lane for sponsors and VIP speakers.",
                    risk_level="MEDIUM",
                    citations=[citations[idx]] if idx < len(citations) else []
                )
                recommendations.append(rec)
                break

    # Fallback if no specific rule matched but relevant historical chunks were found
    if not recommendations and relevant_chunks:
        chunk, doc, _ = relevant_chunks[0]
        recommendations.append(ClubMemoryLessonRecommendation(
            lesson=f"Historical guideline from {doc.filename}",
            historical_context=chunk.content[:180].strip() + "...",
            recommendation="Review the referenced document to ensure alignment with club operating standards.",
            risk_level="LOW",
            citations=[citations[0]] if citations else []
        ))

    overall_risk = "HIGH RISK: Plan timeline or logistics conflict with historical records." if any(r.risk_level == "HIGH" for r in recommendations) else "MEDIUM RISK: Operational cautions surfaced from historical post-mortems."

    return ClubMemoryPlanCheckResponse(
        plan_text=plan_text,
        surfaced_lessons_count=len(recommendations),
        recommendations=recommendations,
        overall_risk_assessment=overall_risk if recommendations else "No historical risks detected."
    )

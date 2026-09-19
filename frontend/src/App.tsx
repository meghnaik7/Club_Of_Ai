import { useEffect, useState } from 'react'
import axios from 'axios'
import './App.css'

function App() {
  const [message, setMessage] = useState('')

  useEffect(() => {
    axios.get('http://localhost:8000/')
      .then(response => {
        setMessage(response.data.message)
      })
      .catch(error => {
        console.error('Error fetching data:', error)
        setMessage('Error connecting to backend')
      })
  }, [])

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="bg-white p-8 rounded-lg shadow-md">
        <h1 className="text-3xl font-bold mb-4 text-blue-600">ClubOps AI Frontend</h1>
        <p className="text-gray-700">Backend says: <span className="font-semibold text-green-600">{message || 'Loading...'}</span></p>
      </div>
    </div>
  )
}

export default App

import React, { useState } from "react";
import './App.css';

function App() {
  const [city, setCity] = useState("");
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    fetch("http://localhost:8000/admin/alert", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        // If your endpoint requires admin token, add:
        // "Authorization": "Bearer <your_admin_token>"
      },
      body: JSON.stringify({ city, message }),
    })
      .then(res => res.json())
      .then(data => setStatus(data.msg || data.detail || "Unknown response"))
      .catch(() => setStatus("error"));
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Send City Alert</h1>
        <form onSubmit={handleSubmit}>
          <input
            type="text"
            placeholder="City"
            value={city}
            onChange={e => setCity(e.target.value)}
            required
          />
          <input
            type="text"
            placeholder="Message"
            value={message}
            onChange={e => setMessage(e.target.value)}
            required
          />
          <button type="submit">Send Alert</button>
        </form>
        {status && <p>Status: {status}</p>}
      </header>
    </div>
  );
}

export default App;
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { loginUser } from '../api/backend';

// Note: backend /login endpoint may not exist yet. The component expects a /login POST that returns user info.
export default function Login({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [status, setStatus] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setStatus(null);
    try {
      const data = await loginUser({ username: username.trim(), password });
      // onLogin should save user to context/localStorage
      onLogin && onLogin(data);
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.response?.data || err.message;
      setStatus({ type: 'error', text: String(msg) });
    }
  }

  return (
    <div style={{ position: 'fixed', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'Segoe UI, Arial', background: '#f4f6fb' }}>
      <div style={{ width: 420, maxWidth: '92%', padding: 20, background: '#fff', borderRadius: 10, boxShadow: '0 6px 20px rgba(20,20,60,0.08)' }}>
        <h2 style={{ marginTop: 0 }}>Sign in</h2>
        <form onSubmit={handleSubmit}>
          <input value={username} onChange={e=>setUsername(e.target.value)} placeholder="Username" required style={inputStyle} />
          <input value={password} onChange={e=>setPassword(e.target.value)} placeholder="Password" type="password" required style={inputStyle} />
          {status && <div style={{ color: status.type==='error' ? '#c00' : '#080', marginBottom: 8 }}>{status.text}</div>}
          <button type="submit" style={buttonStyle}>Sign in</button>
          <div style={{ marginTop: 10, textAlign: 'center', fontSize: 12 }}>
            <span>New here? </span>
            <Link to="/register" style={{ color: '#6c63ff', textDecoration: 'none', fontWeight: 600 }}>
              Sign up
            </Link>
          </div>
          <button type="button" onClick={() => onLogin && onLogin({ username: 'Guest' })} style={{ ...buttonStyle, marginTop: 8, background: '#eee', color: '#333' }}>Continue as Guest</button>
        </form>
      </div>
    </div>
  );
}

const inputStyle = { width: '100%', padding: 10, margin: '8px 0', borderRadius: 8, border: '1px solid #ddd', boxSizing: 'border-box' };
const buttonStyle = { width: '100%', padding: 10, marginTop: 6, borderRadius: 8, background: '#6c63ff', color: '#fff', border: 'none', cursor: 'pointer' };

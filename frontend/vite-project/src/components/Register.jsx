import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { registerUser, loginUser } from '../api/backend';

export default function Register({ onRegister }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [password2, setPassword2] = useState('');
  const [status, setStatus] = useState(null);
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setStatus(null);
    if (password !== password2) return setStatus({ type: 'error', text: 'Passwords do not match' });
    try {
      const normalizedUsername = username.trim();
      const data = await registerUser({ username: normalizedUsername, password });
      const loginData = await loginUser({ username: normalizedUsername, password });
      setStatus({ type: 'success', text: `Registered successfully (id: ${data.id})` });
      setUsername(''); setPassword(''); setPassword2('');
      if (onRegister) {
        onRegister(loginData);
      } else {
        localStorage.setItem('tc_user', JSON.stringify(loginData));
        navigate('/chat');
      }
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.response?.data || err.message;
      setStatus({ type: 'error', text: String(msg) });
    }
  }

  return (
    <div style={{ position: 'fixed', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'Segoe UI, Arial', background: '#f4f6fb' }}>
      <div style={{ width: 420, maxWidth: '92%', padding: 20, background: '#fff', borderRadius: 10, boxShadow: '0 6px 20px rgba(20,20,60,0.08)' }}>
        <h2 style={{ marginTop: 0 }}>Create account</h2>
        <form onSubmit={handleSubmit}>
          <input value={username} onChange={e=>setUsername(e.target.value)} placeholder="Username" required minLength={3} style={inputStyle} />
          <input value={password} onChange={e=>setPassword(e.target.value)} placeholder="Password" type="password" required minLength={6} style={inputStyle} />
          <input value={password2} onChange={e=>setPassword2(e.target.value)} placeholder="Confirm password" type="password" required minLength={6} style={inputStyle} />
          {status && <div style={{ color: status.type==='error' ? '#c00' : '#080', marginBottom: 8 }}>{status.text}</div>}
          <button type="submit" style={buttonStyle}>Register</button>
        </form>
      </div>
    </div>
  );
}

const inputStyle = { width: '100%', padding: 10, margin: '8px 0', borderRadius: 8, border: '1px solid #ddd', boxSizing: 'border-box' };
const buttonStyle = { width: '100%', padding: 10, marginTop: 6, borderRadius: 8, background: '#6c63ff', color: '#fff', border: 'none', cursor: 'pointer' };

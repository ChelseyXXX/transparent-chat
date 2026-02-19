import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Link, useNavigate } from 'react-router-dom';
import ChatLayout from './components/ChatLayout';
import Register from './components/Register';
import Login from './components/Login';

function AppRoutes() {
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('tc_user')); } catch { return null; }
  });
  const navigate = useNavigate();

  function handleLogin(userObj) {
    // save simple user object
    setUser(userObj);
    localStorage.setItem('tc_user', JSON.stringify(userObj));
    navigate('/chat');
  }

  function handleLogout() {
    setUser(null);
    localStorage.removeItem('tc_user');
    navigate('/login');
  }

  return (
    <Routes>
      <Route path="/" element={<Navigate to={user ? '/chat' : '/login'} replace />} />
      <Route path="/login" element={<Login onLogin={handleLogin} />} />
      <Route path="/register" element={<Register onRegister={handleLogin} />} />
      <Route path="/chat" element={user ? <ChatLayout onLogout={handleLogout} user={user} /> : <Navigate to="/login" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div style={{ minHeight: '100vh', background: '#f4f6fb' }}>
        <AppRoutes />
      </div>
    </BrowserRouter>
  );
}

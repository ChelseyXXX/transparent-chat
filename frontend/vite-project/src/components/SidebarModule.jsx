import React, { useState } from 'react';

// Reusable collapsible panel used in the right-side visualization area
export default function SidebarModule({ title, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div style={{ marginBottom: 12, borderRadius: 8, background: '#fff', boxShadow: '0 1px 2px rgba(0,0,0,0.05)', overflow: 'hidden' }}>
      <div
        onClick={() => setOpen((v) => !v)}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 12px',
          cursor: 'pointer',
          background: '#f7f8fb',
          fontWeight: 600,
        }}
      >
        <div>{title}</div>
        <div style={{ fontSize: 14 }}>{open ? '▾' : '▸'}</div>
      </div>
      {open && <div style={{ padding: 12 }}>{children}</div>}
    </div>
  );
}

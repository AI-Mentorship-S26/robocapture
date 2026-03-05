"use client";

import { useEffect, useRef, useState } from "react";

export default function Home() {
  const socketRef = useRef<WebSocket | null>(null);
  const [status, setStatus] = useState("Connecting...");

  useEffect(() => {
    const socket = new WebSocket("ws://localhost:5081/ws");

    socket.onopen = () => {
      setStatus("Connected to .NET ");
      console.log("WebSocket Connected");
    };

    socket.onclose = () => {
      setStatus("Disconnected ");
      console.log("WebSocket Disconnected");
    };

    socket.onerror = (error) => {
      setStatus("Error Connecting ");
      console.error("WebSocket Error:", error);
    };

    socketRef.current = socket;

    // Cleanup connection when you close the tab or refresh
    return () => {
      socket.close();
    };
  }, []);

  const handleClick = () => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      const message = "Hello from Next.js button!";
      socketRef.current.send(message);
      console.log("Sent:", message);
    } else {
      alert("Socket is not open. Check if the .NET backend is running.");
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24 font-sans bg-zinc-50 dark:bg-zinc-950">
      <div className="bg-white dark:bg-zinc-900 p-10 rounded-2xl shadow-lg border border-zinc-200 dark:border-zinc-800 text-center">
        <h1 className="text-2xl font-bold mb-2 dark:text-white">WebSocket Test</h1>
        <p className="text-zinc-500 dark:text-zinc-400 mb-8">
          Status: <span className="font-mono font-bold text-blue-500">{status}</span>
        </p>

        <button
          onClick={handleClick}
          className="bg-black dark:bg-white text-white dark:text-black px-6 py-3 rounded-full font-medium transition-all hover:opacity-80 active:scale-95"
        >
          Send Message to Backend
        </button>
      </div>
    </main>
  );
}
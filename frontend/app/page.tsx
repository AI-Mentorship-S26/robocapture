"use client";

import { useEffect, useRef, useState } from "react";

export default function Home() {
  const socketRef = useRef<WebSocket | null>(null);
  const [status, setStatus] = useState("Connecting...");
  // 1. Add state to hold the message from the backend
  const [receivedMessage, setReceivedMessage] = useState<string>("");
  // Add state to hold image from the backend
  const [imageSrc, setImageSrc] = useState<string>("");

  useEffect(() => {
      const socket = new WebSocket("ws://localhost:5081/ws");
      socket.onopen = () => {
      setStatus("Connected to .NET ");
      console.log("WebSocket Connected");
    };

    // 2. Add the onmessage handler to catch the .NET SendAsync response
    socket.onmessage = (event) => {
      console.log("Received from server:", event.data);

      const data = JSON.parse(event.data);

      if (data.type === "text") {
        setReceivedMessage(data.message); // Update the UI with the backend's message
      }

      if (data.type === "image") {
        setReceivedMessage("Image received from backend");
        setImageSrc(`data:${data.format};base64,${data.data}`);
      }

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

    return () => {
      socket.close();
    };
  }, []);

  const handleClick = () => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      const message = "captureImage";
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
        <p className="text-zinc-500 dark:text-zinc-400 mb-4">
          Status: <span className="font-mono font-bold text-blue-500">{status}</span>
        </p>

        {/* 3. Display the received message in the UI */}
        <div className="mb-8 p-4 bg-zinc-100 dark:bg-zinc-800 rounded-lg min-h-[60px] flex items-center justify-center">
          <p className="text-sm dark:text-zinc-300 italic">
            {receivedMessage ? `Last Message: ${receivedMessage}` : "Waiting for backend response..."}
          </p>
        </div>

        {imageSrc && (
          <div className="mb-6">
            <p className="mb-2 text-sm dark:text-zinc-300">Received Image:</p>
            <img
              src={imageSrc}
              alt="Received from backend"
              className="max-w-full rounded-lg border border-zinc-300 dark:border-zinc-700"
            />
          </div>
        )}

        <button
          onClick={handleClick}
          className="bg-black dark:bg-white text-white dark:text-black px-6 py-3 rounded-full font-medium transition-all hover:opacity-80 active:scale-95"
        >
          Capture Image
        </button>
      </div>
    </main>
  );
}

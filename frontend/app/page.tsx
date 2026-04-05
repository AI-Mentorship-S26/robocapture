"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { supabase } from "@/utils/supabase/client";

export default function Home() {
  const socketRef = useRef<WebSocket | null>(null);
  const [status, setStatus] = useState("Connecting...");
  const [receivedMessage, setReceivedMessage] = useState<string>("");
  const [imageSrc, setImageSrc] = useState<string>("");

  // User state
  const [user, setUser] = useState<any>(null);

  // Image Vectorizer State
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [isVectorizing, setIsVectorizing] = useState(false);
  const [vectorizeStatus, setVectorizeStatus] = useState<{success?: boolean, message?: string} | null>(null);

  useEffect(() => {
    // 1. Get logged in user
    supabase.auth.getUser().then(({ data: { user } }) => {
      setUser(user);
    });

    const { data: authListener } = supabase.auth.onAuthStateChange((event, session) => {
      setUser(session?.user ?? null);
    });

    const socket = new WebSocket("ws://localhost:5081/ws");

    socket.onopen = () => {
      setStatus("Connected to .NET ");
    };

    socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === "image") {
      setReceivedMessage("Image received!");
      setImageSrc(`data:${data.format};base64,${data.data}`);
    } else if (data.type === "no_send") {
      setReceivedMessage(data.message);
    } else if (data.type === "error") {
      setReceivedMessage(`Error: ${data.message}`);
    }
  };
    socket.onclose = () => {
      setStatus("Disconnected ");
    };

    socket.onerror = (error) => {
      setStatus("Error Connecting ");
    };

    socketRef.current = socket;

    // Paste Image Listener
    const handlePaste = (e: ClipboardEvent) => {
      if (e.clipboardData && e.clipboardData.items) {
        const items = e.clipboardData.items;
        for (let i = 0; i < items.length; i++) {
          if (items[i].type.indexOf("image") !== -1) {
            const blob = items[i].getAsFile();
            if (blob) {
              setImageFile(blob);
              
              // Memory leak prevention: revoke old object URL before creating a new one
              setImagePreview((prevPreview) => {
                if (prevPreview) URL.revokeObjectURL(prevPreview);
                return URL.createObjectURL(blob);
              });

              setVectorizeStatus(null);
            }
          }
        }
      }
    };

    window.addEventListener("paste", handlePaste);

    return () => {
      socket.close();
      authListener.subscription.unsubscribe();
      window.removeEventListener("paste", handlePaste);
      if (imagePreview) {
        URL.revokeObjectURL(imagePreview);
      }
    };
  }, [imagePreview]);

  const handleClick = () => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      const message = "captureImage";
      socketRef.current.send(message);
    } else {
      alert("Socket is not open. Check if the .NET backend is running.");
    }
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
  };

  const handleVectorize = async () => {
    if (!imageFile) return;
    setIsVectorizing(true);
    setVectorizeStatus(null);

    const formData = new FormData();
    formData.append("image", imageFile);
    if (user) formData.append("userId", user.id);

    try {
      const response = await fetch("/api/vectorize", {
        method: "POST",
        body: formData,
      });
      const data = await response.json();

      if (response.ok) {
        setVectorizeStatus({ success: true, message: data.message });
      } else {
        setVectorizeStatus({ success: false, message: data.error || "Failed to process image" });
      }
    } catch (e: any) {
      setVectorizeStatus({ success: false, message: e.message });
    } finally {
      setIsVectorizing(false);
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8 font-sans bg-zinc-50 dark:bg-zinc-950">
      <div className="w-full max-w-4xl grid grid-cols-1 md:grid-cols-2 gap-8">
        
        {/* Connection Box */}
        <div className="bg-white dark:bg-zinc-900 p-8 rounded-2xl shadow-lg border border-zinc-200 dark:border-zinc-800 text-center flex flex-col justify-between">
          <div>
            <h1 className="text-2xl font-bold mb-2 dark:text-white">WebSocket Test</h1>
            <p className="text-zinc-500 dark:text-zinc-400 mb-4">
              Status: <span className="font-mono font-bold text-blue-500">{status}</span>
            </p>

            <div className="mb-8 p-4 bg-zinc-100 dark:bg-zinc-800 rounded-lg min-h-[60px] flex items-center justify-center">
              <p className="text-sm dark:text-zinc-300 italic">
                {receivedMessage ? `Last Message: ${receivedMessage}` : "Waiting for backend response..."}
              </p>
            </div>
            {imageSrc && (
              <img src={imageSrc} alt="Captured from Pi" className="max-w-full rounded-lg mt-4 mb-4" />
            )}
          </div>

          <button
            onClick={handleClick}
            className="bg-black dark:bg-white text-white dark:text-black px-6 py-3 rounded-full font-medium transition-all hover:opacity-80 active:scale-95 mb-4 block w-full"
          >
            Send Message to Backend
          </button>
        </div>

        {/* Vectorization Box */}
        <div className="bg-white dark:bg-zinc-900 p-8 rounded-2xl shadow-lg border border-zinc-200 dark:border-zinc-800 text-center flex flex-col justify-between">
          {user ? (
            <div>
              <h2 className="text-xl font-bold mb-2 dark:text-white">Image Vectorizer</h2>
              <p className="text-zinc-500 dark:text-zinc-400 mb-4 text-sm">
                Paste an image (Ctrl+V) anywhere to vectorize it and send to Supabase.
              </p>

              <div className="mb-4 border-2 border-dashed border-zinc-300 dark:border-zinc-700 rounded-lg p-2 min-h-[200px] flex items-center justify-center flex-col">
                {imagePreview ? (
                  <img src={imagePreview} alt="Pasted preview" className="max-h-[180px] object-contain rounded" />
                ) : (
                  <p className="text-zinc-400 text-sm">No image pasted yet</p>
                )}
              </div>

              {vectorizeStatus && (
                <p className={`text-sm mb-4 ${vectorizeStatus.success ? "text-green-500" : "text-red-500"}`}>
                  {vectorizeStatus.message}
                </p>
              )}

              <button
                onClick={handleVectorize}
                disabled={!imagePreview || isVectorizing}
                className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:bg-blue-600 text-white px-6 py-3 rounded-full font-medium transition-all active:scale-95 w-full mb-3"
              >
                {isVectorizing ? "Vectorizing & Saving..." : "Vectorize Image"}
              </button>
              
              <button onClick={handleLogout} className="text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 text-sm font-semibold mt-2">
                Log Out
              </button>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full">
              <h2 className="text-xl font-bold mb-4 dark:text-white">Login required</h2>
              <p className="text-zinc-500 dark:text-zinc-400 mb-6 text-sm">You must be logged in to vectorize images.</p>
              <Link
                href="/login"
                className="bg-blue-600 text-white px-6 py-3 rounded-full font-medium transition-all hover:bg-blue-700 active:scale-95 block w-full text-center"
              >
                Go to Login Page
              </Link>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

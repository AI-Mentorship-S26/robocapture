"use client";

import Link from "next/link";
import ASMRBackground from "@/components/ui/asmr-background";

export default function LandingPage() {
  return (
    <ASMRBackground>
      <div className="flex flex-col items-center gap-8 px-6">
        {/* Logo / Title */}
        <div className="text-center">
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight text-white">
            Robo<span className="text-blue-400">Capture</span>
          </h1>
          <div className="w-full h-px bg-linear-to-r from-transparent via-white/10 to-transparent my-6" />
          <p className="text-sm md:text-base text-white tracking-[0.4em] uppercase font-light">
            Adaptive Visual Intelligence for Robotics
          </p>
        </div>

        {/* Login Button */}
        <Link
          href="/login"
          className="group relative mt-4 inline-flex items-center justify-center"
        >
          <div className="absolute inset-0 rounded-full bg-blue-500/20 blur-xl transition-all duration-300 group-hover:bg-blue-500/30 group-hover:blur-2xl" />
          <span className="relative inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/4 px-8 py-3 text-sm font-medium tracking-widest text-white uppercase backdrop-blur-sm transition-all duration-300 hover:border-white/20 hover:bg-white/8 hover:text-white">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="opacity-50 transition-opacity group-hover:opacity-80"
            >
              <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
              <polyline points="10 17 15 12 10 7" />
              <line x1="15" y1="12" x2="3" y2="12" />
            </svg>
            Sign In
          </span>
        </Link>


      </div>
    </ASMRBackground>
  );
}

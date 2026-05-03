"use client";

import { useMemo, useState } from "react";
import { GalleryImage } from "@/types/dashboard";
import { GridIcon } from "./icons";

interface Props {
  galleryLoading: boolean;
  galleryImages: GalleryImage[];
  onSelect: (url: string) => void;
}

export default function GalleryView({ galleryLoading, galleryImages, onSelect }: Props) {
  const [filterModel, setFilterModel] = useState("all");
  const [filterDate,  setFilterDate]  = useState<"all" | "today" | "week" | "month">("all");

  const availableModels = useMemo(
    () => Array.from(new Set(galleryImages.map((img) => img.model))).sort(),
    [galleryImages]
  );

  const filteredImages = useMemo(() => {
    const now = new Date();
    return galleryImages.filter(({ model, capturedAt }) => {
      if (filterModel !== "all" && model !== filterModel) return false;
      if (filterDate === "all") return true;
      const captured = new Date(capturedAt);
      if (filterDate === "today") return captured.toDateString() === now.toDateString();
      const cutoff = new Date(now);
      if (filterDate === "week")  cutoff.setDate(now.getDate() - 7);
      if (filterDate === "month") cutoff.setMonth(now.getMonth() - 1);
      return captured >= cutoff;
    });
  }, [galleryImages, filterModel, filterDate]);

  return (
    <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-sm flex flex-col">
      <div className="px-4 py-3 border-b border-white/[0.05] flex items-center justify-between">
        <span className="text-[10px] font-semibold text-white tracking-widest uppercase">Saved Images</span>
        <span className="font-mono text-[11px] text-white">
          {filteredImages.length}{filteredImages.length !== galleryImages.length ? ` / ${galleryImages.length}` : ""} images
        </span>
      </div>

      {galleryImages.length > 0 && (
        <div className="px-4 py-3 border-b border-white/4 flex flex-col gap-2.5">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[9px] text-white uppercase tracking-widest w-12 shrink-0">Model</span>
            {["all", ...availableModels].map((m) => (
              <button
                key={m}
                onClick={() => setFilterModel(m)}
                className={`font-mono text-[9px] px-2 py-1 rounded-md border transition-all duration-150 cursor-pointer ${
                  filterModel === m
                    ? "bg-blue-500/15 border-blue-500/30 text-blue-400"
                    : "border-white/[0.06] text-white hover:text-white hover:border-white/15"
                }`}
              >
                {m === "all" ? "All" : m.replace(/_/g, " ")}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[9px] text-white uppercase tracking-widest w-12 shrink-0">Date</span>
            {(["all", "today", "week", "month"] as const).map((d) => (
              <button
                key={d}
                onClick={() => setFilterDate(d)}
                className={`text-[9px] px-2 py-1 rounded-md border transition-all duration-150 cursor-pointer ${
                  filterDate === d
                    ? "bg-blue-500/15 border-blue-500/30 text-blue-400"
                    : "border-white/[0.06] text-white hover:text-white hover:border-white/15"
                }`}
              >
                {d === "all" ? "All time" : d === "today" ? "Today" : d === "week" ? "This week" : "This month"}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="p-5">
        {galleryLoading ? (
          <div className="flex items-center justify-center h-40">
            <span className="text-[11px] text-white animate-pulse">Loading gallery…</span>
          </div>
        ) : galleryImages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-40 gap-3">
            <GridIcon size={22} className="text-white" />
            <p className="text-[11px] text-white text-center">
              No saved images yet.<br />Reward an image on the live feed to save it here.
            </p>
          </div>
        ) : filteredImages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-40 gap-3">
            <GridIcon size={22} className="text-white" />
            <p className="text-[11px] text-white text-center">No images match the current filters.</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {filteredImages.map(({ name, url, model, capturedAt }) => (
              <button
                key={name}
                onClick={() => onSelect(url)}
                className="rounded-lg overflow-hidden bg-[#161619] border border-white/[0.06] hover:border-white/20 transition-all duration-200 cursor-pointer group flex flex-col"
              >
                <div className="aspect-video w-full overflow-hidden">
                  <img
                    src={url}
                    alt={name}
                    className="w-full h-full object-cover group-hover:opacity-75 transition-opacity duration-200"
                  />
                </div>
                <div className="px-2.5 py-2 flex items-center justify-between gap-2">
                  <span className="font-mono text-[9px] text-white truncate">
                    {new Date(capturedAt).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                  </span>
                  <span className="shrink-0 font-mono text-[8px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 uppercase tracking-wide">
                    {model.replace(/_/g, " ")}
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

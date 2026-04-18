"use client";

import { BarChart, Bar, ResponsiveContainer, Tooltip, Cell } from "recharts";

interface Props {
  data: { step: string; reward: number }[];
  height?: number;
  cellOpacityRange?: [number, number];
  barRadius?: number;
}

export default function RewardChart({
  data,
  height = 64,
  cellOpacityRange = [0.2, 0.7],
  barRadius = 2,
}: Props) {
  const [minOpacity, maxOpacity] = cellOpacityRange;

  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} barCategoryGap="20%">
          <Tooltip
            cursor={false}
            contentStyle={{
              background: "#161619",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: "6px",
              fontSize: "10px",
              color: "rgba(255,255,255,0.6)",
              padding: "4px 8px",
            }}
            itemStyle={{ color: "#3B82F6" }}
            labelStyle={{ display: "none" }}
          />
          <Bar dataKey="reward" radius={[barRadius, barRadius, 0, 0]}>
            {data.map((_, index) => (
              <Cell
                key={index}
                fill={
                  index === data.length - 1
                    ? "#3B82F6"
                    : `rgba(59,130,246,${minOpacity + (index / data.length) * (maxOpacity - minOpacity)})`
                }
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function Sparkline({ data, color }: { data: number[]; color: string }) {
  const w = 80;
  const h = 28;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const bw = w / data.length;

  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="w-full" preserveAspectRatio="none" role="img" aria-label="Sparkline chart">
      {data.map((v, i) => {
        const bh = ((v - min) / range) * h;
        return (
          <rect
            key={i}
            x={i * bw}
            y={h - bh}
            width={Math.max(bw - 0.5, 1)}
            height={bh}
            fill={color}
            opacity={0.5}
            rx={1}
          />
        );
      })}
    </svg>
  );
}

export default function LoadingSkeleton({ rows = 6 }) {
  return (
    <div style={{ padding: 20 }}>
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          style={{
            height: 16,
            marginBottom: 12,
            borderRadius: 8,
            background: 'linear-gradient(90deg, #ffffff10 25%, #ffffff1d 37%, #ffffff10 63%)',
            backgroundSize: '400% 100%',
            animation: 'pulse 1.4s ease infinite',
          }}
        />
      ))}
      <style>{`@keyframes pulse {0% {background-position: 100% 50%;} 100% {background-position: 0 50%;}}`}</style>
    </div>
  )
}

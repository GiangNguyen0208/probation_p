export function PageHeader({ title }: { title: string }) {
  return (
    <h1
      className="text-xl font-bold mb-2"
      style={{ color: "var(--tg-text-color)" }}
    >
      {title}
    </h1>
  );
}
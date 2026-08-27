export function Reports({ markdown }: { markdown: string }) {
  return (
    <section>
      <h2>리포트</h2>
      <pre className="report">{markdown}</pre>
    </section>
  );
}

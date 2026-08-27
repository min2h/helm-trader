export function Reports({ markdown }: { markdown: string }) {
  return (
    <section>
      <div className="page-head">
        <div>
          <p className="eyebrow">일일</p>
          <h2>리포트</h2>
        </div>
      </div>
      <pre className="report card">{markdown || "아직 저장된 보고서가 없습니다."}</pre>
    </section>
  );
}

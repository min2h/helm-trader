export const MARKET_MODE: Record<string, string> = {
  spot: "현물만",
  futures: "선물만",
  both: "현물+선물",
};

export const SYMBOL_SELECTION: Record<string, string> = {
  ai_auto: "AI 추천 자동",
  manual: "사용자 고정 목록",
  ai_approve: "AI 추천 후 승인",
};

export const STRATEGY_MODE: Record<string, string> = {
  trend: "추세추종",
  funding_arb: "펀딩 차익",
  grid: "횡보 그리드",
  regime_auto: "레짐 자동선택",
};

export const RISK_GRADE: Record<string, string> = {
  conservative: "보수",
  standard: "표준",
  aggressive: "공격",
};

export const AI_LEVEL: Record<string, string> = {
  off: "끔 (룰베이스)",
  params_only: "일일 파라미터 제안",
  params_and_symbols: "파라미터 + 종목 추천",
};

export const STOP_STYLE: Record<string, string> = {
  fixed_pct: "고정 %",
  atr: "ATR 배수",
  trailing: "트레일링",
};

export const RUN_STATE: Record<string, string> = {
  running: "가동 중",
  soft_stop: "소프트 정지",
  hard_kill: "하드 킬",
};

export const SCHEDULE: Record<string, string> = {
  every_15m: "15분마다",
  every_1h: "1시간마다",
  daily_0800: "매일 08:00",
};

export function labelOf(map: Record<string, string>, value: unknown): string {
  const key = String(value ?? "");
  return map[key] ?? (key || "—");
}

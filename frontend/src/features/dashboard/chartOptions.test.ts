import { describe, expect, it } from "vitest";
import { riskOption, timelineOption } from "./chartOptions";

describe("dashboard chart options", () => {
  it("maps risk counters to four categories", () => {
    const option = riskOption({
      events: 10,
      sessions: 3,
      unique_source_ips: 2,
      successful_login_sessions: 1,
      download_sessions: 1,
      risk_low: 4,
      risk_medium: 3,
      risk_high: 2,
      risk_critical: 1,
      latest_event_at: null,
    });
    const series = option.series as Array<{ data: Array<{ value: number }> }>;
    expect(series[0].data.map((item) => item.value)).toEqual([4, 3, 2, 1]);
  });

  it("maps timeline points into event and session series", () => {
    const option = timelineOption({
      hours: 2,
      points: [
        { timestamp: "2026-06-25T10:00:00Z", events: 7, sessions: 2 },
        { timestamp: "2026-06-25T11:00:00Z", events: 9, sessions: 3 },
      ],
    });
    const series = option.series as Array<{ data: number[] }>;
    expect(series[0].data).toEqual([7, 9]);
    expect(series[1].data).toEqual([2, 3]);
  });
});

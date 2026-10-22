import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { ApiError } from "./api";
import { docProblem, hubStrategy, pinnedLine, strategyError } from "./strategy";
import { PREVIEW_RAIDS, previewStrategy } from "./preview/strategy-fake";

const DOC = "https://docs.google.com/document/d/";

describe("strategy docs", () => {
  it("takes only https Google Docs and Drive links, as the API does", () => {
    expect(docProblem(`${DOC}abc/edit`)).toBeNull();
    expect(
      docProblem("https://drive.google.com/file/d/abc/view", "Naxx"),
    ).toBeNull();
    for (const bad of [
      "",
      "   ",
      "http://docs.google.com/document/d/x",
      "https://example.com/doc",
      "not a link",
      "https://docs.google.com.evil.example/x",
      "https://user:pw@docs.google.com/x",
      `${DOC}${"x".repeat(500)}`,
    ]) {
      expect(docProblem(bad), bad).not.toBeNull();
    }
    expect(docProblem(`${DOC}abc`, "x".repeat(81))).toMatch(/80 characters/);
  });

  it("lists the same raids as the hub, in its order", () => {
    const service = readFileSync(
      new URL(
        "../../../../services/api/src/toads_api/strategy/service.py",
        import.meta.url,
      ),
      "utf8",
    );
    const raids = [
      ...service.matchAll(/Raid\("([a-z0-9]+)", "([^"]+)", "([^"]+)"\)/g),
    ].map(([, id, short, name]) => ({ id, short, name }));
    expect(PREVIEW_RAIDS).toEqual(raids);
  });

  it("says who pinned a doc, and when", () => {
    expect(
      pinnedLine({ added_at: "2026-10-22T18:00:00Z", added_by: "Hopscotch" }),
    ).toBe("Pinned 22 Oct by Hopscotch");
    expect(
      pinnedLine({ added_at: "2026-10-22T18:00:00Z", added_by: null }),
    ).toBe("Pinned 22 Oct");
  });

  it("explains refusals", () => {
    expect(strategyError(new ApiError(403, "Forbidden"))).toMatch(
      /Only officers/,
    );
    expect(strategyError(new ApiError(404, "gone"))).toMatch(/taken it down/);
    expect(strategyError(new ApiError(422, "Pick one of the raids"))).toBe(
      "Pick one of the raids",
    );
    expect(strategyError(new ApiError(500, ""))).toMatch(/try again/);
    expect(strategyError(new Error("boom"))).toMatch(/try again/);
  });

  it("calls the hub routes", async () => {
    const calls: [string, RequestInit | undefined][] = [];
    const f = (async (path: string, init?: RequestInit) => {
      calls.push([path, init]);
      return new Response(init?.method === "DELETE" ? null : "{}", {
        status: init?.method === "DELETE" ? 204 : 200,
      });
    }) as typeof fetch;
    const hub = hubStrategy(f);
    await hub.library();
    await hub.pin("naxx", `${DOC}1`, "", { through: null, night: "sun" });
    await hub.remove(7, null);
    await hub.pin("naxx", `${DOC}1`, "", { through: "wed", night: null });
    await hub.pin("naxx", `${DOC}1`, "", { through: "wed", night: "wed" });
    await hub.remove(7, "wed");
    await hub.night("wed");
    await hub.setNight("wed", ["zg", "bwl"]);
    expect(calls.map(([p, i]) => `${i?.method ?? "GET"} ${p}`)).toEqual([
      "GET /api/strategy",
      "POST /api/admin/strategy",
      "DELETE /api/admin/strategy/7",
      "POST /api/days/wed/strategy/docs",
      "POST /api/days/wed/strategy/docs",
      "DELETE /api/days/wed/strategy/docs/7",
      "GET /api/days/wed/strategy",
      "PUT /api/days/wed/strategy",
    ]);
    const body = (n: number) => JSON.parse(String(calls[n][1]?.body));
    expect(body(1)).toEqual({
      raid: "naxx",
      url: `${DOC}1`,
      title: "",
      raid_day: "sun",
    });
    expect(body(3).every_night).toBe(true);
    expect(body(4).every_night).toBe(false);
    expect(body(7)).toEqual({ raids: ["zg", "bwl"] });
  });

  it("works the preview from samples", async () => {
    const wed = await previewStrategy.night("wed");
    expect(wed.raids.map((r) => [r.raid.short, r.pinned?.title])).toEqual([
      ["ZG", "Zul'Gurub strategy"],
      ["BWL", "BWL full clear"],
    ]);
    expect((await previewStrategy.night("sun")).raids[0].pinned?.title).toBe(
      "Sunday MC (fast clear)",
    );
    const pinned = await previewStrategy.pin(
      "naxx",
      ` ${DOC}naxx `,
      "  Naxx   full clear ",
      { through: "wed", night: "wed" },
    );
    expect(pinned.title).toBe("Naxx full clear");
    expect(
      (await previewStrategy.night("wed")).raids.map((r) => r.raid.id),
    ).toEqual(["zg", "bwl", "naxx"]);
    const aq = await previewStrategy.pin("aq40", `${DOC}aq`, "", {
      through: null,
      night: null,
    });
    expect(aq.title).toBe("Temple of Ahn'Qiraj strategy");
    await expect(
      previewStrategy.pin("naxx", "https://example.com", "", {
        through: null,
        night: null,
      }),
    ).rejects.toBeInstanceOf(ApiError);
    await expect(
      previewStrategy.pin("kara", `${DOC}k`, "", {
        through: null,
        night: null,
      }),
    ).rejects.toBeInstanceOf(ApiError);
    const naxx = (await previewStrategy.library()).raids.find(
      (r) => r.raid.id === "naxx",
    );
    expect(naxx?.slots.map((s) => [s.name, s.pinned.id])).toEqual([
      ["Wednesday", pinned.id],
    ]);
    const mc = (await previewStrategy.library()).raids.find(
      (r) => r.raid.id === "mc",
    );
    expect(mc?.slots.map((s) => s.name)).toEqual(["Every night", "Sunday"]);
    const sunDoc = mc!.slots[1].pinned;
    await expect(
      previewStrategy.remove(sunDoc.id, "wed"),
    ).rejects.toBeInstanceOf(ApiError);
    await previewStrategy.remove(pinned.id, "wed");
    await expect(
      previewStrategy.remove(pinned.id, null),
    ).rejects.toBeInstanceOf(ApiError);
    for (let i = 0; i < 8; i++)
      await previewStrategy.pin("tbd", `${DOC}t${i}`, "", {
        through: null,
        night: null,
      });
    const tbd = (await previewStrategy.library()).raids.find(
      (r) => r.raid.id === "tbd",
    );
    expect(tbd?.slots[0].replaced).toHaveLength(5);
    expect(
      (await previewStrategy.setNight("thu", ["naxx", "naxx"])).raids,
    ).toEqual([{ raid: PREVIEW_RAIDS[5], pinned: null }]);
    await expect(
      previewStrategy.setNight("thu", ["kara"]),
    ).rejects.toBeInstanceOf(ApiError);
    expect((await previewStrategy.setNight("thu", [])).raids).toEqual([]);
    expect(
      (await previewStrategy.library()).nights.map((n) => n.raid_day),
    ).toContain("thu");
  });
});

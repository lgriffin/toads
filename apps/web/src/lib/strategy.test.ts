import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { ApiError } from "./api";
import {
  addedLine,
  docOptions,
  docProblem,
  hubStrategy,
  strategyError,
} from "./strategy";
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

  it("says who added a doc, and when", () => {
    expect(
      addedLine({ added_at: "2026-10-22T18:00:00Z", added_by: "Hopscotch" }),
    ).toBe("Added 22 Oct by Hopscotch");
    expect(
      addedLine({ added_at: "2026-10-22T18:00:00Z", added_by: null }),
    ).toBe("Added 22 Oct");
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
    await hub.add("naxx", `${DOC}1`, "", null);
    await hub.remove(7, null);
    await hub.add("naxx", `${DOC}1`, "Naxx", "wed");
    await hub.remove(7, "wed");
    await hub.night("wed");
    await hub.setNight("wed", [3, 1]);
    expect(calls.map(([p, i]) => `${i?.method ?? "GET"} ${p}`)).toEqual([
      "GET /api/strategy",
      "POST /api/admin/strategy",
      "DELETE /api/admin/strategy/7",
      "POST /api/days/wed/strategy/docs",
      "DELETE /api/days/wed/strategy/docs/7",
      "GET /api/days/wed/strategy",
      "PUT /api/days/wed/strategy",
    ]);
    const body = (n: number) => JSON.parse(String(calls[n][1]?.body));
    expect(body(3)).toEqual({ raid: "naxx", url: `${DOC}1`, title: "Naxx" });
    expect(body(6)).toEqual({ docs: [3, 1] });
  });

  it("works the preview from samples", async () => {
    const wed = await previewStrategy.night("wed");
    expect(wed.docs.map((d) => [d.raid.short, d.doc.title])).toEqual([
      ["ZG", "Zul'Gurub strategy"],
      ["BWL", "BWL full clear"],
    ]);
    expect((await previewStrategy.night("sun")).docs[0].doc.title).toBe(
      "Sunday MC (fast clear)",
    );
    expect((await previewStrategy.night("thu")).docs).toEqual([]);
    const added = await previewStrategy.add(
      "naxx",
      ` ${DOC}naxx `,
      "  Naxx   full clear ",
      "wed",
    );
    expect(added.title).toBe("Naxx full clear");
    expect((await previewStrategy.night("wed")).docs).toHaveLength(2);
    expect(
      (await previewStrategy.add("aq40", `${DOC}aq`, "", null)).title,
    ).toBe("Temple of Ahn'Qiraj strategy");
    await expect(
      previewStrategy.add("naxx", "https://example.com", "", null),
    ).rejects.toBeInstanceOf(ApiError);
    await expect(
      previewStrategy.add("kara", `${DOC}k`, "", null),
    ).rejects.toBeInstanceOf(ApiError);
    let library = await previewStrategy.library();
    expect(
      library.raids
        .find((r) => r.raid.id === "naxx")
        ?.docs.map((d) => [d.title, d.nights]),
    ).toEqual([["Naxx full clear", []]]);
    expect(docOptions(library).slice(0, 2)).toEqual([
      {
        id: String(library.raids[0].docs[0].id),
        short: "MC",
        name: "Sunday MC (fast clear)",
      },
      {
        id: String(library.raids[0].docs[1].id),
        short: "MC",
        name: "Molten Core strategy",
      },
    ]);
    const night = await previewStrategy.setNight("thu", [added.id, added.id]);
    expect(night.docs.map((d) => d.doc.id)).toEqual([added.id]);
    await expect(previewStrategy.setNight("thu", [999])).rejects.toBeInstanceOf(
      ApiError,
    );
    await expect(
      previewStrategy.remove(added.id, "wed"),
    ).rejects.toBeInstanceOf(ApiError);
    await previewStrategy.remove(added.id, "thu");
    expect((await previewStrategy.night("thu")).docs).toEqual([]);
    await expect(previewStrategy.remove(added.id, null)).rejects.toBeInstanceOf(
      ApiError,
    );
    for (let i = 0; i < 20; i++)
      await previewStrategy.add("tbd", `${DOC}t${i}`, "", null);
    await expect(
      previewStrategy.add("tbd", `${DOC}more`, "", null),
    ).rejects.toThrow(/take an old one down/);
    library = await previewStrategy.library();
    expect(library.nights.map((n) => n.raid_day)).toContain("thu");
  });
});

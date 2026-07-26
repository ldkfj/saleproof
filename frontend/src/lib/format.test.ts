import { describe, it, expect } from "vitest";
import { weiToGen, centsToPrice, shortAddr, timeAgo, jsonReplacer } from "./format";

describe("format utils", () => {
  describe("weiToGen", () => {
    it("formats integer wei amounts correctly", () => {
      expect(weiToGen(0n)).toBe("0 GEN");
      expect(weiToGen(1000000000000000000n)).toBe("1 GEN");
      expect(weiToGen(20000000000000000000n)).toBe("20 GEN");
    });

    it("formats fractional wei amounts accurately with BigInt math", () => {
      expect(weiToGen(1900000000000000000n)).toBe("1.9 GEN");
      expect(weiToGen(500000000000000000n)).toBe("0.5 GEN");
      expect(weiToGen(1234500000000000000n)).toBe("1.2345 GEN");
      expect(weiToGen(123400000000000000n)).toBe("0.1234 GEN");
    });

    it("accepts string and number inputs", () => {
      expect(weiToGen("1900000000000000000")).toBe("1.9 GEN");
    });
  });

  describe("centsToPrice", () => {
    it("formats GBP, USD, EUR, JPY, VND correctly", () => {
      expect(centsToPrice(5177, "GBP")).toBe("£51.77");
      expect(centsToPrice(6500, "USD")).toBe("$65.00");
      expect(centsToPrice(1200, "EUR")).toBe("€12.00");
      expect(centsToPrice(500, "JPY")).toBe("¥5.00");
      expect(centsToPrice(10000, "VND")).toBe("₫100.00");
    });
  });

  describe("shortAddr", () => {
    it("truncates address with ellipses", () => {
      expect(shortAddr("0x7885536194BbD6E1D0A6Ab991aB215CFa9542339")).toBe("0x7885...2339");
      expect(shortAddr("0x123")).toBe("0x123");
      expect(shortAddr("")).toBe("");
    });
  });

  describe("timeAgo", () => {
    it("formats past and future relative times", () => {
      const now = Math.floor(Date.now() / 1000);
      expect(timeAgo(now - 10)).toBe("10s ago");
      expect(timeAgo(now - 120)).toBe("2m ago");
      expect(timeAgo(now + 120)).toBe("in 2m");
    });
  });

  describe("jsonReplacer", () => {
    it("serializes BigInt to string in JSON.stringify", () => {
      const data = { id: 1n, amount: 1000000000000000000n };
      const jsonStr = JSON.stringify(data, jsonReplacer);
      expect(jsonStr).toBe('{"id":"1","amount":"1000000000000000000"}');
    });
  });
});

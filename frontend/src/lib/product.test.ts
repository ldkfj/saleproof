import { describe, expect, it } from "vitest";
import { buildAddProductRequest } from "./product";

const BOND = "0x1111111111111111111111111111111111111111";

describe("buildAddProductRequest", () => {
  it("builds a nonpayable add_product request for a valid URL", () => {
    const request = buildAddProductRequest(
      BOND,
      "  https://merchant.example/product  ",
    );

    expect(request).toEqual({
      address: BOND,
      functionName: "add_product",
      args: ["https://merchant.example/product"],
    });
    expect(request).not.toHaveProperty("value");
  });

  it("rejects an invalid URL before submission", () => {
    expect(() => buildAddProductRequest(BOND, "merchant.example/product")).toThrow(
      "http:// or https://",
    );
  });
});

import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import type { Product } from "../lib/contracts";

vi.mock("../lib/chain", () => ({
  BOND_ADDRESS: "0x1111111111111111111111111111111111111111",
}));
vi.mock("./TxAction", () => ({ TxAction: () => null }));

import { MerchantSetupActions } from "./MerchantSetupActions";

const product: Product = {
  id: 1,
  url: "https://merchant.example/product",
  merchant: "0x2222222222222222222222222222222222222222",
  registered_at: 1_710_000_000,
  active: true,
};

describe("MerchantSetupActions", () => {
  it("mounts first-product and first-sale controls for an active merchant", () => {
    const html = renderToStaticMarkup(
      <MerchantSetupActions
        products={[product]}
        merchantActive
        saleCount={0}
        onSuccess={vi.fn()}
      />,
    );

    expect(html).toContain("Add Product");
    expect(html).toContain("Announce Your First Sale");
    expect(html).toContain("Product #1");
    expect(html).toContain("GBP");
  });

  it("renders no merchant setup controls for an inactive merchant", () => {
    const html = renderToStaticMarkup(
      <MerchantSetupActions
        products={[product]}
        merchantActive={false}
        saleCount={0}
        onSuccess={vi.fn()}
      />,
    );
    expect(html).toBe("");
  });
});

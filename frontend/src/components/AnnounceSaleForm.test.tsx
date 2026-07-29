import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import type { Product } from "../lib/contracts";

const captured = vi.hoisted(() => ({
  request: undefined as
    | (() => {
        address: string;
        functionName: string;
        args: readonly (number | string)[];
        value?: bigint;
      })
    | undefined,
  onSuccess: undefined as (() => Promise<void> | void) | undefined,
  disabled: undefined as boolean | undefined,
}));

vi.mock("../lib/chain", () => ({
  BOND_ADDRESS: "0x1111111111111111111111111111111111111111",
}));

vi.mock("./TxAction", () => ({
  TxAction: (props: {
    request: typeof captured.request;
    onSuccess: typeof captured.onSuccess;
    disabled?: boolean;
  }) => {
    captured.request = props.request;
    captured.onSuccess = props.onSuccess;
    captured.disabled = props.disabled;
    return null;
  },
}));

import { AnnounceSaleForm } from "./AnnounceSaleForm";

const product: Product = {
  id: 1,
  url: "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
  merchant: "0x2222222222222222222222222222222222222222",
  registered_at: 1_710_000_000,
  active: true,
};

describe("AnnounceSaleForm", () => {
  it("renders the zero-sale creation path and builds exact five-argument calldata", async () => {
    const refresh = vi.fn();
    const html = renderToStaticMarkup(
      <AnnounceSaleForm
        products={[product]}
        merchantActive
        saleCount={0}
        onSuccess={refresh}
      />,
    );

    expect(html).toContain("Announce Your First Sale");
    expect(html).toContain("Create the first sale directly from this dashboard");
    expect(html).toContain("GBP");
    expect(captured.disabled).toBe(false);

    const request = captured.request?.();
    expect(request).toEqual({
      address: "0x1111111111111111111111111111111111111111",
      functionName: "announce_sale",
      args: [1, 6_500, 2_000, 86_400, "GBP"],
    });
    expect(request).not.toHaveProperty("value");

    await captured.onSuccess?.();
    expect(refresh).toHaveBeenCalledOnce();
  });
});

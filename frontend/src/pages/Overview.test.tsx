import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Merchant, Product, Sale } from "../lib/contracts";

const fixtures = vi.hoisted(() => ({
  address: null as string | null,
  walletMerchant: null as Merchant | null,
  products: [] as Product[],
  sales: [] as Sale[],
}));

vi.mock("react", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react")>();
  return {
    ...actual,
    useState: <T,>(initialState: T | (() => T)) => {
      if (initialState === null && fixtures.walletMerchant !== null) {
        return actual.useState(fixtures.walletMerchant as T);
      }
      return actual.useState(initialState);
    },
  };
});
vi.mock("../lib/store", () => ({
  useProtocolData: () => ({
    loading: false,
    error: null,
    products: fixtures.products,
    observationsMap: {},
    sales: fixtures.sales,
    claims: [],
    config: null,
    refresh: vi.fn(),
  }),
}));
vi.mock("../lib/wallet", () => ({
  useWallet: () => ({ address: fixtures.address }),
}));
vi.mock("../lib/chain", () => ({
  BOND_ADDRESS: "0x1111111111111111111111111111111111111111",
  GL_NETWORK_LABEL: "Studionet",
}));
vi.mock("../lib/contracts", () => ({
  bondContract: {
    getMerchant: vi.fn(),
    getWithdrawable: vi.fn(),
  },
}));
vi.mock("../components/TxAction", () => ({ TxAction: () => null }));
vi.mock("../components/PrepaidTxAction", () => ({ PrepaidTxAction: () => null }));

import { Overview } from "./Overview";

const euroSale: Sale = {
  id: 1,
  merchant: "0x2222222222222222222222222222222222222222",
  product_id: 1,
  claimed_ref_price_cents: 6_500,
  claimed_discount_bp: 2_000,
  currency: "EUR",
  announced_at: 1_710_000_000,
  ends_at: 1_710_086_400,
  observation_count_at_announcement: 3,
  claim_id: 0,
  active: true,
};

describe("Overview", () => {
  beforeEach(() => {
    fixtures.address = null;
    fixtures.walletMerchant = null;
    fixtures.products = [];
    fixtures.sales = [];
  });

  it("renders each sale using its decoded currency rather than hardcoded GBP", () => {
    fixtures.sales = [euroSale];

    const html = renderToStaticMarkup(
      <MemoryRouter>
        <Overview />
      </MemoryRouter>,
    );

    expect(html).toContain("\u20ac65.00");
    expect(html).not.toContain("\u00a365.00");
  });

  it("mounts both setup forms for an active merchant with no products or sales", () => {
    const merchantAddress = "0x2222222222222222222222222222222222222222";
    fixtures.address = merchantAddress;
    fixtures.walletMerchant = {
      addr: merchantAddress,
      name: "Fresh Shop",
      bond_wei: 2_000_000_000_000_000_000n,
      strikes: 0,
      active: true,
      joined_at: 1_710_000_000,
    };

    const html = renderToStaticMarkup(
      <MemoryRouter>
        <Overview />
      </MemoryRouter>,
    );

    expect(html).toContain("Add Product");
    expect(html).toContain("Announce Your First Sale");
    expect(html).toContain("No Products Registered");
    expect(html).toContain("No Sales Announced");
  });
});

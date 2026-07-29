import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

vi.mock("../lib/store", () => ({
  useProtocolData: () => ({
    loading: false,
    error: null,
    products: [],
    observationsMap: {},
    sales: [
      {
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
      },
    ],
    claims: [],
    config: null,
    refresh: vi.fn(),
  }),
}));
vi.mock("../lib/wallet", () => ({ useWallet: () => ({ address: null }) }));
vi.mock("../lib/chain", () => ({
  BOND_ADDRESS: "0x1111111111111111111111111111111111111111",
  GL_NETWORK_LABEL: "Studionet",
}));
vi.mock("../lib/contracts", () => ({ bondContract: {} }));
vi.mock("../components/TxAction", () => ({ TxAction: () => null }));
vi.mock("../components/PrepaidTxAction", () => ({ PrepaidTxAction: () => null }));
vi.mock("../components/MerchantSetupActions", () => ({
  MerchantSetupActions: () => null,
}));

import { Overview } from "./Overview";

describe("Overview sale currency", () => {
  it("renders each sale using its decoded currency rather than hardcoded GBP", () => {
    const html = renderToStaticMarkup(
      <MemoryRouter>
        <Overview />
      </MemoryRouter>,
    );

    expect(html).toContain("\u20ac65.00");
    expect(html).not.toContain("\u00a365.00");
  });
});

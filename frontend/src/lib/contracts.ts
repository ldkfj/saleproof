import { TransactionHashVariant } from "genlayer-js/types";
import { client, LEDGER_ADDRESS, BOND_ADDRESS } from "./chain";

export interface Product {
  id: number;
  url: string;
  merchant: string;
  registered_at: number;
  active: boolean;
}

export interface Observation {
  price_cents: number;
  currency: string;
  observed_at: number;
  watcher: string;
  ok: boolean;
  note: string;
}

export interface Sale {
  id: number;
  merchant: string;
  product_id: number;
  claimed_ref_price_cents: number;
  claimed_discount_bp: number;
  currency: string;
  announced_at: number;
  ends_at: number;
  observation_count_at_announcement: number;
  claim_id: number;
  active: boolean;
}

export interface Claim {
  id: number;
  sale_id: number;
  buyer: string;
  deposit_wei: bigint;
  state: "OPEN" | "JUDGED" | "APPEALED" | "FINAL" | "SETTLED" | string;
  verdict: "GENUINE" | "INFLATED_REFERENCE" | "DECEPTIVE" | "INSUFFICIENT_EVIDENCE" | "" | string;
  confidence_bp: number;
  reasoning: string;
  appellant: string;
  appeal_bond_wei: bigint;
  original_verdict: string;
  created_at: number;
  judged_at: number;
}

export interface Merchant {
  addr: string;
  name: string;
  bond_wei: bigint;
  strikes: number;
  active: boolean;
  joined_at: number;
}

export interface ProtocolConfig {
  owner: string;
  ledger: string;
  min_bond_wei: bigint;
  claim_deposit_wei: bigint;
  appeal_bond_wei: bigint;
  appeal_window_s: number;
  strike_limit: number;
  pool_wei: bigint;
}

export interface LedgerConfig {
  owner: string;
  snapshot_cooldown_s: number;
  max_observations: number;
}

function num(val: any): number {
  if (typeof val === "bigint") return Number(val);
  if (typeof val === "number") return val;
  return Number(val || 0);
}

function big(val: any): bigint {
  if (typeof val === "bigint") return val;
  if (typeof val === "number" || typeof val === "string") return BigInt(val);
  return 0n;
}

function decodeObservationInt(value: unknown): number {
  if (typeof value === "bigint") return Number(value);
  if (typeof value === "number") return value;
  if (typeof value === "string" && /^\d+$/.test(value)) return Number(value);
  return Number.NaN;
}

export function decodeObservation(o: any): Observation {
  return {
    price_cents: decodeObservationInt(o.price_cents),
    currency: String(o.currency ?? ""),
    observed_at: decodeObservationInt(o.observed_at),
    watcher: String(o.watcher ?? ""),
    ok: o.ok === true,
    note: String(o.note ?? ""),
  };
}

export function decodeSale(s: any): Sale {
  return {
    id: num(s.id),
    merchant: String(s.merchant ?? ""),
    product_id: num(s.product_id),
    claimed_ref_price_cents: num(s.claimed_ref_price_cents),
    claimed_discount_bp: num(s.claimed_discount_bp),
    currency: String(s.currency ?? ""),
    announced_at: num(s.announced_at),
    ends_at: num(s.ends_at),
    observation_count_at_announcement: num(
      s.observation_count_at_announcement,
    ),
    claim_id: num(s.claim_id),
    active: s.active === true,
  };
}

export const ledgerContract = {
  async getConfig(): Promise<LedgerConfig> {
    const cfg: any = await client.readContract({
      address: LEDGER_ADDRESS as `0x${string}`,
      functionName: "get_config",
      args: [],
      transactionHashVariant: TransactionHashVariant.LATEST_FINAL,
    });
    return {
      owner: String(cfg.owner || ""),
      snapshot_cooldown_s: num(cfg.snapshot_cooldown_s),
      max_observations: num(cfg.max_observations),
    };
  },

  async getProductCount(): Promise<number> {
    const res = await client.readContract({
      address: LEDGER_ADDRESS as `0x${string}`,
      functionName: "get_product_count",
      args: [],
      transactionHashVariant: TransactionHashVariant.LATEST_FINAL,
    });
    return num(res);
  },

  async getProduct(productId: number): Promise<Product> {
    const p: any = await client.readContract({
      address: LEDGER_ADDRESS as `0x${string}`,
      functionName: "get_product",
      args: [productId],
      transactionHashVariant: TransactionHashVariant.LATEST_FINAL,
    });
    return {
      id: num(p.id),
      url: String(p.url || ""),
      merchant: String(p.merchant || ""),
      registered_at: num(p.registered_at),
      active: Boolean(p.active),
    };
  },

  async getObservations(productId: number): Promise<Observation[]> {
    const res: any = await client.readContract({
      address: LEDGER_ADDRESS as `0x${string}`,
      functionName: "get_observations",
      args: [productId],
      transactionHashVariant: TransactionHashVariant.LATEST_FINAL,
    });
    const list = Array.isArray(res) ? res : [];
    return list.map(decodeObservation);
  },

  async getRecentObservations(productId: number, k: number): Promise<Observation[]> {
    const res: any = await client.readContract({
      address: LEDGER_ADDRESS as `0x${string}`,
      functionName: "get_recent_observations",
      args: [productId, k],
      transactionHashVariant: TransactionHashVariant.LATEST_FINAL,
    });
    const list = Array.isArray(res) ? res : [];
    return list.map(decodeObservation);
  },

  async isRegistrar(addr: string): Promise<boolean> {
    const res = await client.readContract({
      address: LEDGER_ADDRESS as `0x${string}`,
      functionName: "is_registrar",
      args: [addr],
      transactionHashVariant: TransactionHashVariant.LATEST_FINAL,
    });
    return Boolean(res);
  },
};

export const bondContract = {
  async getCounts(): Promise<{ sale_count: number; claim_count: number }> {
    const res: any = await client.readContract({
      address: BOND_ADDRESS as `0x${string}`,
      functionName: "get_counts",
      args: [],
      transactionHashVariant: TransactionHashVariant.LATEST_FINAL,
    });
    return {
      sale_count: num(res?.sale_count),
      claim_count: num(res?.claim_count),
    };
  },

  async getSale(saleId: number): Promise<Sale> {
    const s: any = await client.readContract({
      address: BOND_ADDRESS as `0x${string}`,
      functionName: "get_sale",
      args: [saleId],
      transactionHashVariant: TransactionHashVariant.LATEST_FINAL,
    });
    return decodeSale(s);
  },

  async getClaim(claimId: number): Promise<Claim> {
    const c: any = await client.readContract({
      address: BOND_ADDRESS as `0x${string}`,
      functionName: "get_claim",
      args: [claimId],
      transactionHashVariant: TransactionHashVariant.LATEST_FINAL,
    });
    return {
      id: num(c.id),
      sale_id: num(c.sale_id),
      buyer: String(c.buyer || ""),
      deposit_wei: big(c.deposit_wei),
      state: String(c.state || "OPEN"),
      verdict: String(c.verdict || ""),
      confidence_bp: num(c.confidence_bp),
      reasoning: String(c.reasoning || ""),
      appellant: String(c.appellant || ""),
      appeal_bond_wei: big(c.appeal_bond_wei),
      original_verdict: String(c.original_verdict || ""),
      created_at: num(c.created_at),
      judged_at: num(c.judged_at),
    };
  },

  async getMerchant(addr: string): Promise<Merchant> {
    const m: any = await client.readContract({
      address: BOND_ADDRESS as `0x${string}`,
      functionName: "get_merchant",
      args: [addr],
      transactionHashVariant: TransactionHashVariant.LATEST_FINAL,
    });
    return {
      addr: String(m.addr || addr),
      name: String(m.name || ""),
      bond_wei: big(m.bond_wei),
      strikes: num(m.strikes),
      active: Boolean(m.active),
      joined_at: num(m.joined_at),
    };
  },

  async getConfig(): Promise<ProtocolConfig> {
    const cfg: any = await client.readContract({
      address: BOND_ADDRESS as `0x${string}`,
      functionName: "get_config",
      args: [],
      transactionHashVariant: TransactionHashVariant.LATEST_FINAL,
    });
    return {
      owner: String(cfg.owner || ""),
      ledger: String(cfg.ledger || ""),
      min_bond_wei: big(cfg.min_bond_wei),
      claim_deposit_wei: big(cfg.claim_deposit_wei),
      appeal_bond_wei: big(cfg.appeal_bond_wei),
      appeal_window_s: num(cfg.appeal_window_s),
      strike_limit: num(cfg.strike_limit),
      pool_wei: big(cfg.pool_wei),
    };
  },

  async getWithdrawable(addr: string): Promise<{ addr: string; amount_wei: bigint }> {
    const w: any = await client.readContract({
      address: BOND_ADDRESS as `0x${string}`,
      functionName: "get_withdrawable",
      args: [addr],
      transactionHashVariant: TransactionHashVariant.LATEST_FINAL,
    });
    return {
      addr: String(w.addr || addr),
      amount_wei: big(w.amount_wei),
    };
  },
};

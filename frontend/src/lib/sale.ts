import type { Observation, Sale } from "./contracts";

export const THIRTY_DAYS_S = 2_592_000;
export const SALE_CURRENCIES = ["USD", "EUR", "GBP", "JPY", "VND"] as const;

export type SaleCurrency = (typeof SALE_CURRENCIES)[number];

export interface AnnounceSaleInput {
  productId: number;
  referencePrice: string;
  discountPercent: string;
  durationSeconds: number;
  currency: string;
}

export interface EligibleSaleEvidence {
  eligibleObservations: Observation[];
  chartObservations: Observation[];
  lowestPriceCents: number | null;
}

export function isSaleCurrency(value: string): value is SaleCurrency {
  return SALE_CURRENCIES.some((currency) => currency === value);
}

export function parseScaledDecimal(
  input: string,
  decimals: number,
  label: string,
): number {
  const value = input.trim();
  if (!/^\d+(?:\.\d+)?$/.test(value)) {
    throw new Error(`Enter a valid ${label}.`);
  }
  const [whole, fraction = ""] = value.split(".");
  if (fraction.length > decimals) {
    throw new Error(`${label} may have at most ${decimals} decimal places.`);
  }
  const scaled =
    BigInt(whole) * 10n ** BigInt(decimals) +
    BigInt(fraction.padEnd(decimals, "0") || "0");
  if (scaled > BigInt(Number.MAX_SAFE_INTEGER)) {
    throw new Error(`${label} is too large.`);
  }
  return Number(scaled);
}

export function buildAnnounceSaleArgs(
  input: AnnounceSaleInput,
): [number, number, number, number, SaleCurrency] {
  if (!Number.isInteger(input.productId) || input.productId < 1) {
    throw new Error("Select a valid product.");
  }
  const referencePriceCents = parseScaledDecimal(
    input.referencePrice,
    2,
    "reference price",
  );
  if (referencePriceCents < 1 || referencePriceCents > 1_000_000_000) {
    throw new Error("Reference price is outside the contract range.");
  }
  const discountBp = parseScaledDecimal(
    input.discountPercent,
    2,
    "discount",
  );
  if (discountBp < 100 || discountBp > 9_500) {
    throw new Error("Discount must be between 1% and 95%.");
  }
  if (
    !Number.isInteger(input.durationSeconds) ||
    input.durationSeconds < 600 ||
    input.durationSeconds > THIRTY_DAYS_S
  ) {
    throw new Error("Duration is outside the contract range.");
  }
  if (!isSaleCurrency(input.currency)) {
    throw new Error("Select a supported currency.");
  }
  return [
    input.productId,
    referencePriceCents,
    discountBp,
    input.durationSeconds,
    input.currency,
  ];
}

export function getEligibleSaleEvidence(
  observations: readonly Observation[],
  sale: Pick<
    Sale,
    "announced_at" | "currency" | "observation_count_at_announcement"
  >,
): EligibleSaleEvidence {
  const frozenCount = Number.isFinite(sale.observation_count_at_announcement)
    ? Math.max(0, Math.trunc(sale.observation_count_at_announcement))
    : 0;
  const cutoff = Math.min(observations.length, frozenCount);
  const announcedAt = Number.isFinite(sale.announced_at)
    ? Math.max(0, Math.trunc(sale.announced_at))
    : 0;
  const windowStart = Math.max(0, announcedAt - THIRTY_DAYS_S);
  const eligibleObservations = observations.slice(0, cutoff).filter((observation) => {
    if (observation.ok !== true) return false;
    if (
      typeof observation.price_cents !== "number" ||
      !Number.isInteger(observation.price_cents) ||
      observation.price_cents < 1 ||
      observation.price_cents > 1_000_000_000
    ) {
      return false;
    }
    if (observation.currency !== sale.currency) return false;
    if (
      typeof observation.observed_at !== "number" ||
      !Number.isInteger(observation.observed_at)
    ) {
      return false;
    }
    return (
      observation.observed_at >= windowStart &&
      observation.observed_at <= announcedAt
    );
  });

  const lowestPriceCents =
    eligibleObservations.length === 0
      ? null
      : eligibleObservations.reduce(
          (lowest, observation) => Math.min(lowest, observation.price_cents),
          eligibleObservations[0].price_cents,
        );

  return {
    eligibleObservations,
    chartObservations: eligibleObservations.slice(-50),
    lowestPriceCents,
  };
}

import { createClient, chains } from "genlayer-js";

export const LEDGER_ADDRESS = (import.meta.env.VITE_LEDGER_ADDRESS || "").trim();
export const BOND_ADDRESS = (import.meta.env.VITE_BOND_ADDRESS || "").trim();

export const isConfigValid = Boolean(
  LEDGER_ADDRESS &&
  LEDGER_ADDRESS.startsWith("0x") &&
  BOND_ADDRESS &&
  BOND_ADDRESS.startsWith("0x")
);

export const client = createClient({
  chain: chains.studionet,
});

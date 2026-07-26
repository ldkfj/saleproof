import { createClient, chains } from "genlayer-js";

export type GlNetwork = "studionet" | "testnet_bradbury";

const requestedNetwork = (import.meta.env.VITE_GL_NETWORK || "studionet").trim();

export const GL_NETWORK: GlNetwork =
  requestedNetwork === "testnet_bradbury" ? "testnet_bradbury" : "studionet";
export const GL_CHAIN =
  GL_NETWORK === "testnet_bradbury" ? chains.testnetBradbury : chains.studionet;
export const IS_STUDIONET = GL_NETWORK === "studionet";
export const GL_NETWORK_LABEL =
  GL_NETWORK === "testnet_bradbury" ? "Testnet Bradbury" : "Studionet";
export const GL_CHAIN_ID_HEX = `0x${GL_CHAIN.id.toString(16)}`;
export const GL_RPC_URL = GL_CHAIN.rpcUrls.default.http[0];
export const GL_EXPLORER_URL = GL_CHAIN.blockExplorers!.default.url.replace(/\/$/, "");

export const LEDGER_ADDRESS = (import.meta.env.VITE_LEDGER_ADDRESS || "").trim();
export const BOND_ADDRESS = (import.meta.env.VITE_BOND_ADDRESS || "").trim();

export const isConfigValid = Boolean(
  LEDGER_ADDRESS &&
  LEDGER_ADDRESS.startsWith("0x") &&
  BOND_ADDRESS &&
  BOND_ADDRESS.startsWith("0x")
);

export const client = createClient({
  chain: GL_CHAIN,
});

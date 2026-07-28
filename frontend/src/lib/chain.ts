import { createClient, chains } from "genlayer-js";

const requestedNetwork = (import.meta.env.VITE_GL_NETWORK || "studionet").trim();
if (requestedNetwork !== "studionet") {
  throw new Error("SaleProof's current reviewed release supports Studionet only.");
}

export const GL_NETWORK = "studionet" as const;
export const GL_CHAIN = chains.studionet;
export const IS_STUDIONET = true;
export const GL_NETWORK_LABEL = "Studionet";
export const GL_CHAIN_ID_HEX = `0x${GL_CHAIN.id.toString(16)}`;
export const GL_RPC_URL = GL_CHAIN.rpcUrls.default.http[0];
export const GL_EXPLORER_URL = GL_CHAIN.blockExplorers!.default.url.replace(/\/$/, "");

export const LEDGER_ADDRESS = (import.meta.env.VITE_LEDGER_ADDRESS || "").trim();
export const BOND_ADDRESS = (import.meta.env.VITE_BOND_ADDRESS || "").trim();

function isContractAddress(value: string): boolean {
  return (
    /^0x[0-9a-fA-F]{40}$/.test(value) &&
    value.toLowerCase() !== "0x0000000000000000000000000000000000000000"
  );
}

export const isConfigValid = Boolean(
  isContractAddress(LEDGER_ADDRESS) && isContractAddress(BOND_ADDRESS)
);

export const client = createClient({
  chain: GL_CHAIN,
});

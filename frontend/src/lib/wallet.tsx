import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { createAccount, createClient, generatePrivateKey } from "genlayer-js";
import {
  GL_CHAIN,
  GL_CHAIN_ID_HEX,
  GL_NETWORK_LABEL,
  GL_RPC_URL,
  GL_EXPLORER_URL,
  IS_STUDIONET,
} from "./chain";

const BURNER_KEY_STORAGE = "saleproof.studionet.burner-private-key";
export const STUDIONET_FAUCET_AMOUNT_WEI = 1_000_000_000_000_000_000;

export function studionetFaucetRequest(address: `0x${string}`) {
  return {
    method: "sim_fundAccount" as const,
    params: [address, STUDIONET_FAUCET_AMOUNT_WEI] as [`0x${string}`, number],
  };
}

export type ProviderKind = "injected" | "burner";
export type WalletClient = ReturnType<typeof createClient>;

interface Eip1193Provider {
  request(args: { method: string; params?: unknown[] | Record<string, unknown> }): Promise<unknown>;
}

declare global {
  interface Window {
    ethereum?: Eip1193Provider;
  }
}

interface WalletContextValue {
  address: `0x${string}` | null;
  balance: bigint | null;
  providerKind: ProviderKind | null;
  client: WalletClient | null;
  connecting: boolean;
  funding: boolean;
  error: string | null;
  connectInjected: () => Promise<void>;
  connectBurner: () => Promise<void>;
  disconnect: () => void;
  fundBurner: () => Promise<void>;
  refreshBalance: () => Promise<void>;
}

const WalletContext = createContext<WalletContextValue | null>(null);

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

async function ensureSelectedNetwork(provider: Eip1193Provider): Promise<void> {
  const currentChainId = await provider.request({ method: "eth_chainId" });
  if (
    typeof currentChainId === "string" &&
    currentChainId.toLowerCase() === GL_CHAIN_ID_HEX.toLowerCase()
  ) {
    return;
  }

  try {
    await provider.request({
      method: "wallet_switchEthereumChain",
      params: [{ chainId: GL_CHAIN_ID_HEX }],
    });
  } catch (error) {
    const code =
      typeof error === "object" && error !== null && "code" in error
        ? Number((error as { code: unknown }).code)
        : 0;
    if (code !== 4902) throw error;

    await provider.request({
      method: "wallet_addEthereumChain",
      params: [
        {
          chainId: GL_CHAIN_ID_HEX,
          chainName: GL_CHAIN.name,
          nativeCurrency: GL_CHAIN.nativeCurrency,
          rpcUrls: [GL_RPC_URL],
          blockExplorerUrls: [GL_EXPLORER_URL],
        },
      ],
    });
    await provider.request({
      method: "wallet_switchEthereumChain",
      params: [{ chainId: GL_CHAIN_ID_HEX }],
    });
  }
}

export const WalletProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [address, setAddress] = useState<`0x${string}` | null>(null);
  const [balance, setBalance] = useState<bigint | null>(null);
  const [providerKind, setProviderKind] = useState<ProviderKind | null>(null);
  const [client, setClient] = useState<WalletClient | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [funding, setFunding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshBalance = useCallback(async () => {
    if (!client || !address) return;
    try {
      const nextBalance = await client.getBalance({ address });
      setBalance(nextBalance);
    } catch (nextError) {
      setError(`Unable to read wallet balance: ${errorMessage(nextError)}`);
    }
  }, [address, client]);

  useEffect(() => {
    if (!address || !client) {
      setBalance(null);
      return;
    }

    void refreshBalance();
    const timer = window.setInterval(() => void refreshBalance(), 10_000);
    return () => window.clearInterval(timer);
  }, [address, client, refreshBalance]);

  const connectInjected = useCallback(async () => {
    setConnecting(true);
    setError(null);
    try {
      const provider = window.ethereum;
      if (!provider) throw new Error("MetaMask or another EIP-1193 wallet was not found.");

      const accounts = (await provider.request({ method: "eth_requestAccounts" })) as string[];
      if (!accounts[0]?.startsWith("0x")) throw new Error("The wallet returned no account.");
      await ensureSelectedNetwork(provider);

      const nextAddress = accounts[0] as `0x${string}`;
      const nextClient = createClient({
        chain: GL_CHAIN,
        account: nextAddress,
        provider,
      });
      setAddress(nextAddress);
      setClient(nextClient);
      setProviderKind("injected");
    } catch (nextError) {
      setError(errorMessage(nextError));
    } finally {
      setConnecting(false);
    }
  }, []);

  const connectBurner = useCallback(async () => {
    setConnecting(true);
    setError(null);
    try {
      if (!IS_STUDIONET) {
        throw new Error("The dev burner is available on Studionet only.");
      }
      let privateKey = localStorage.getItem(BURNER_KEY_STORAGE) as `0x${string}` | null;
      if (!privateKey?.startsWith("0x") || privateKey.length !== 66) {
        privateKey = generatePrivateKey();
        localStorage.setItem(BURNER_KEY_STORAGE, privateKey);
      }

      const account = createAccount(privateKey);
      const nextClient = createClient({ chain: GL_CHAIN, account });
      setAddress(account.address);
      setClient(nextClient);
      setProviderKind("burner");
    } catch (nextError) {
      setError(errorMessage(nextError));
    } finally {
      setConnecting(false);
    }
  }, []);

  const disconnect = useCallback(() => {
    setAddress(null);
    setBalance(null);
    setProviderKind(null);
    setClient(null);
    setError(null);
  }, []);

  const fundBurner = useCallback(async () => {
    if (!client || !address || providerKind !== "burner" || !IS_STUDIONET) return;
    setFunding(true);
    setError(null);
    try {
      await client.request(studionetFaucetRequest(address));
      await refreshBalance();
    } catch (nextError) {
      setError(`${GL_NETWORK_LABEL} faucet failed: ${errorMessage(nextError)}`);
    } finally {
      setFunding(false);
    }
  }, [address, client, providerKind, refreshBalance]);

  const value = useMemo(
    () => ({
      address,
      balance,
      providerKind,
      client,
      connecting,
      funding,
      error,
      connectInjected,
      connectBurner,
      disconnect,
      fundBurner,
      refreshBalance,
    }),
    [
      address,
      balance,
      client,
      connectBurner,
      connectInjected,
      connecting,
      disconnect,
      error,
      fundBurner,
      funding,
      providerKind,
      refreshBalance,
    ],
  );

  return <WalletContext.Provider value={value}>{children}</WalletContext.Provider>;
};

export function useWallet(): WalletContextValue {
  const context = useContext(WalletContext);
  if (!context) throw new Error("useWallet must be used within WalletProvider");
  return context;
}

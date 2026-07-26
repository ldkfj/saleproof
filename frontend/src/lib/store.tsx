import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { ledgerContract, bondContract } from "./contracts";
import type {
  Product,
  Observation,
  Sale,
  Claim,
  ProtocolConfig,
  LedgerConfig,
} from "./contracts";
import { GL_NETWORK_LABEL, isConfigValid } from "./chain";

export interface ProtocolStoreState {
  isConfigValid: boolean;
  loading: boolean;
  error: string | null;
  lastUpdated: number | null;
  secondsAgo: number;
  productCount: number;
  products: Product[];
  observationsMap: Record<number, Observation[]>;
  saleCount: number;
  sales: Sale[];
  claimCount: number;
  claims: Claim[];
  config: ProtocolConfig | null;
  ledgerConfig: LedgerConfig | null;
  ledgerConfigUnavailable: boolean;
  refresh: () => Promise<void>;
}

const ProtocolContext = createContext<ProtocolStoreState | null>(null);

export const ProtocolProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<number | null>(null);
  const [secondsAgo, setSecondsAgo] = useState<number>(0);

  const [productCount, setProductCount] = useState<number>(0);
  const [products, setProducts] = useState<Product[]>([]);
  const [observationsMap, setObservationsMap] = useState<Record<number, Observation[]>>({});

  const [saleCount, setSaleCount] = useState<number>(0);
  const [sales, setSales] = useState<Sale[]>([]);
  const [claimCount, setClaimCount] = useState<number>(0);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [config, setConfig] = useState<ProtocolConfig | null>(null);
  const [ledgerConfig, setLedgerConfig] = useState<LedgerConfig | null>(null);
  const [ledgerConfigUnavailable, setLedgerConfigUnavailable] = useState(false);

  useEffect(() => {
    if (!isConfigValid) return;

    let active = true;
    void ledgerContract
      .getConfig()
      .then((nextConfig) => {
        if (!active) return;
        setLedgerConfig(nextConfig);
        setLedgerConfigUnavailable(false);
      })
      .catch(() => {
        if (!active) return;
        setLedgerConfig(null);
        setLedgerConfigUnavailable(true);
      });

    return () => {
      active = false;
    };
  }, []);

  const fetchData = useCallback(async () => {
    if (!isConfigValid) {
      setError("Contract addresses are not configured properly in .env.");
      setLoading(false);
      return;
    }

    try {
      setError(null);

      const [pCount, counts, pConfig] = await Promise.all([
        ledgerContract.getProductCount().catch(() => 0),
        bondContract.getCounts().catch(() => ({ sale_count: 0, claim_count: 0 })),
        bondContract.getConfig().catch(() => null),
      ]);

      setProductCount(pCount);
      setSaleCount(counts.sale_count);
      setClaimCount(counts.claim_count);
      setConfig(pConfig);

      const productPromises: Promise<Product | null>[] = [];
      const obsPromises: Promise<{ id: number; obs: Observation[] }>[] = [];
      for (let i = 1; i <= pCount; i++) {
        productPromises.push(ledgerContract.getProduct(i).catch(() => null));
        obsPromises.push(
          ledgerContract
            .getObservations(i)
            .then((obs) => ({ id: i, obs }))
            .catch(() => ({ id: i, obs: [] }))
        );
      }

      const salePromises: Promise<Sale | null>[] = [];
      for (let i = 1; i <= counts.sale_count; i++) {
        salePromises.push(bondContract.getSale(i).catch(() => null));
      }

      const claimPromises: Promise<Claim | null>[] = [];
      for (let i = 1; i <= counts.claim_count; i++) {
        claimPromises.push(bondContract.getClaim(i).catch(() => null));
      }

      const [fetchedProducts, fetchedObsList, fetchedSales, fetchedClaims] = await Promise.all([
        Promise.all(productPromises),
        Promise.all(obsPromises),
        Promise.all(salePromises),
        Promise.all(claimPromises),
      ]);

      const validProducts = fetchedProducts.filter((p): p is Product => p !== null);
      setProducts(validProducts);

      const obsMap: Record<number, Observation[]> = {};
      fetchedObsList.forEach(({ id, obs }) => {
        obsMap[id] = obs;
      });
      setObservationsMap(obsMap);

      const validSales = fetchedSales.filter((s): s is Sale => s !== null);
      setSales(validSales);

      const validClaims = fetchedClaims.filter((c): c is Claim => c !== null);
      setClaims(validClaims);

      const now = Date.now();
      setLastUpdated(now);
      setSecondsAgo(0);
    } catch (err: any) {
      console.error("Error fetching protocol data:", err);
      setError(err?.message || `Failed to fetch on-chain data from ${GL_NETWORK_LABEL}.`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();

    const interval = setInterval(() => {
      if (!document.hidden) {
        fetchData();
      }
    }, 15000);

    const handleVisibilityChange = () => {
      if (!document.hidden) {
        fetchData();
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      clearInterval(interval);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [fetchData]);

  useEffect(() => {
    const timer = setInterval(() => {
      if (lastUpdated) {
        setSecondsAgo(Math.floor((Date.now() - lastUpdated) / 1000));
      }
    }, 1000);
    return () => clearInterval(timer);
  }, [lastUpdated]);

  return (
    <ProtocolContext.Provider
      value={{
        isConfigValid,
        loading,
        error,
        lastUpdated,
        secondsAgo,
        productCount,
        products,
        observationsMap,
        saleCount,
        sales,
        claimCount,
        claims,
        config,
        ledgerConfig,
        ledgerConfigUnavailable,
        refresh: fetchData,
      }}
    >
      {children}
    </ProtocolContext.Provider>
  );
};

export function useProtocolData(): ProtocolStoreState {
  const context = useContext(ProtocolContext);
  if (!context) {
    throw new Error("useProtocolData must be used within a ProtocolProvider");
  }
  return context;
}

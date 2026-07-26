import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ProtocolProvider, useProtocolData } from "./lib/store";
import { WalletProvider } from "./lib/wallet";
import { ConfigError } from "./components/ConfigError";
import { Header } from "./components/Header";
import { Overview } from "./pages/Overview";
import { ProductDetail } from "./pages/ProductDetail";
import { SaleDetail } from "./pages/SaleDetail";
import { ClaimDetail } from "./pages/ClaimDetail";
import { MerchantDetail } from "./pages/MerchantDetail";

const MainLayout: React.FC = () => {
  const { isConfigValid } = useProtocolData();

  if (!isConfigValid) {
    return <ConfigError />;
  }

  return (
    <div className="app-container">
      <Header />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/product/:id" element={<ProductDetail />} />
          <Route path="/sale/:id" element={<SaleDetail />} />
          <Route path="/claim/:id" element={<ClaimDetail />} />
          <Route path="/merchant/:addr" element={<MerchantDetail />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
};

export function App() {
  return (
    <WalletProvider>
      <ProtocolProvider>
        <BrowserRouter>
          <MainLayout />
        </BrowserRouter>
      </ProtocolProvider>
    </WalletProvider>
  );
}

export default App;

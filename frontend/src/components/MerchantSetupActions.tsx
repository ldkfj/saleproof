import React from "react";
import type { Product } from "../lib/contracts";
import { AddProductForm } from "./AddProductForm";
import { AnnounceSaleForm } from "./AnnounceSaleForm";

interface MerchantSetupActionsProps {
  products: Product[];
  merchantActive: boolean;
  saleCount: number;
  onSuccess: () => Promise<void> | void;
}

export const MerchantSetupActions: React.FC<MerchantSetupActionsProps> = ({
  products,
  merchantActive,
  saleCount,
  onSuccess,
}) => {
  if (!merchantActive) return null;
  return (
    <>
      <AddProductForm merchantActive onSuccess={onSuccess} />
      <AnnounceSaleForm
        products={products}
        merchantActive
        saleCount={saleCount}
        onSuccess={onSuccess}
      />
    </>
  );
};

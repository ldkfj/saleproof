import { TransactionStatus } from "genlayer-js/types";
import type {
  CalldataEncodable,
  GenLayerTransaction,
  LeaderReceipt,
  TransactionHash,
} from "genlayer-js/types";
import { GL_EXPLORER_URL } from "./chain";
import type { WalletClient } from "./wallet";

export function explorerTxUrl(hash: string): string {
  return `${GL_EXPLORER_URL}/transactions/${hash}`;
}

export const ERROR_MESSAGES: Record<string, string> = {
  ERR_ACTIVE_SALES: "End or cancel all active sales before withdrawing the bond.",
  ERR_ALREADY_MERCHANT: "This wallet is already an active merchant.",
  ERR_ALREADY_REGISTRAR: "This address is already a registrar.",
  ERR_APPEAL_BOND: "The requested appeal bond must match the configured amount.",
  ERR_APPEAL_WINDOW_CLOSED: "The appeal window has closed.",
  ERR_APPEAL_WINDOW_OPEN: "The appeal window is still open.",
  ERR_BAD_ADDRESS: "The supplied address is invalid.",
  ERR_BAD_TRANSITION: "This action is not valid for the current claim state.",
  ERR_BAD_VERDICT: "The verdict is not recognized.",
  ERR_BANNED: "This merchant reached the strike limit and cannot re-register.",
  ERR_BOND_COVERAGE: "The merchant bond cannot cover another worst-case claim.",
  ERR_COOLDOWN: "The snapshot cooldown has not elapsed.",
  ERR_DEPOSIT: "The requested claim deposit must match the configured amount.",
  ERR_DISCOUNT: "Discount must be between 1% and 95%.",
  ERR_SALE_ALREADY_CLAIMED: "This sale already has its canonical claim.",
  ERR_DURATION: "Sale duration must be between 10 minutes and 30 days.",
  ERR_EXTRACT_INVALID: "Validators could not produce a valid price extraction.",
  ERR_INACTIVE: "This product is inactive.",
  ERR_INSUFFICIENT_CREDIT:
    "Withdrawable prepaid credit is below the amount required for this action.",
  ERR_INSOLVENT: "The merchant bond cannot cover this settlement.",
  ERR_MERCHANT_INACTIVE: "This merchant is inactive.",
  ERR_MIN_BOND: "The supplied bond is below the configured minimum.",
  ERR_NAME: "Merchant name is required and must be at most 100 characters.",
  ERR_NO_CLAIM: "The claim does not exist.",
  ERR_NO_MERCHANT: "This wallet is not a registered merchant.",
  ERR_NO_PRODUCT: "The product does not exist.",
  ERR_NO_SALE: "The sale does not exist.",
  ERR_NOT_APPELLANT: "This wallet is not eligible to appeal this verdict.",
  ERR_NOT_MERCHANT: "Connect a registered merchant wallet for this action.",
  ERR_NOT_OWNER: "Only the contract owner may perform this action.",
  ERR_NOT_REGISTRAR: "This address is not an authorized registrar.",
  ERR_NOT_YOUR_PRODUCT: "The selected product belongs to another merchant.",
  ERR_NOT_YOUR_SALE: "Only the merchant who announced this sale may cancel it.",
  ERR_NOTHING_TO_WITHDRAW: "This wallet has no withdrawable balance.",
  ERR_OBS_CAP: "This product has reached its observation limit.",
  ERR_OPEN_CLAIMS: "Settle all claims before withdrawing the merchant bond.",
  ERR_PRICE: "Reference price is outside the supported range.",
  ERR_PRODUCT_INACTIVE: "The selected product is inactive.",
  ERR_SALE_CLOSED: "The sale claim window has closed.",
  ERR_SALE_HAS_CLAIMS: "A sale with claims cannot be canceled.",
  ERR_SALE_INACTIVE: "This sale is inactive.",
  ERR_SELF_CLAIM: "A merchant cannot file a claim against their own sale.",
  ERR_URL_DUPLICATE: "This active product URL is already registered.",
  ERR_URL_EMPTY: "A product URL is required.",
  ERR_URL_SCHEME: "Product URL must start with http:// or https://.",
  ERR_URL_TOO_LONG: "Product URL must be at most 500 characters.",
  ERR_VERDICT_INVALID: "Validators returned a malformed verdict.",
  ERR_ZERO_VALUE: "Top-up amount must be greater than zero.",
};

export interface WriteRequest {
  address: `0x${string}`;
  functionName: string;
  args?: CalldataEncodable[];
  value?: bigint;
}

export interface TransactionFailure {
  code: string | null;
  message: string;
  details: string;
}

export class FinalizedTransactionError extends Error {
  readonly failure: TransactionFailure;

  constructor(failure: TransactionFailure) {
    super(failure.code ? `${failure.code}: ${failure.message}` : failure.message);
    this.name = "FinalizedTransactionError";
    this.failure = failure;
  }
}

function leaderReceipts(transaction: GenLayerTransaction): LeaderReceipt[] {
  const receipts = transaction.consensus_data?.leader_receipt;
  return Array.isArray(receipts) ? receipts : [];
}

export function isExecutionSuccess(transaction: GenLayerTransaction): boolean {
  const leader = leaderReceipts(transaction).find((receipt) => receipt.mode === "leader");
  return leader?.execution_result === "SUCCESS";
}

export function transactionFailure(transaction: GenLayerTransaction): TransactionFailure {
  const receipts = leaderReceipts(transaction);
  const leader = receipts.find((receipt) => receipt.mode === "leader");
  const failedReceipts = (leader ? [leader] : receipts).filter(
    (receipt) =>
      receipt.execution_result !== "SUCCESS" &&
      !JSON.stringify(receipt).toLowerCase().includes('"payload":"idle"'),
  );
  const details = JSON.stringify(failedReceipts.length > 0 ? failedReceipts : transaction);
  const code = details.match(/ERR_[A-Z_]+/)?.[0] ?? null;
  return {
    code,
    message: code
      ? ERROR_MESSAGES[code] ?? "The contract rejected this transaction."
      : "The transaction finalized, but contract execution failed.",
    details,
  };
}

export async function submitAndFinalize(
  client: WalletClient,
  request: WriteRequest,
  onHash: (hash: `0x${string}`) => void,
): Promise<GenLayerTransaction> {
  const hash = (await client.writeContract({
    address: request.address,
    functionName: request.functionName,
    args: request.args ?? [],
    value: request.value ?? 0n,
  })) as `0x${string}`;
  onHash(hash);

  return waitForFinalizedSuccess(client, hash);
}

export async function waitForFinalizedSuccess(
  client: WalletClient,
  hash: `0x${string}`,
): Promise<GenLayerTransaction> {
  const receipt = await client.waitForTransactionReceipt({
    hash: hash as TransactionHash,
    status: TransactionStatus.FINALIZED,
    interval: 3_000,
    retries: 200,
  });
  if (!isExecutionSuccess(receipt)) {
    throw new FinalizedTransactionError(transactionFailure(receipt));
  }
  return receipt;
}

export function genToWei(input: string): bigint {
  const value = input.trim();
  if (!/^\d+(?:\.\d+)?$/.test(value)) {
    throw new Error("Enter a non-negative GEN amount.");
  }
  const [whole, fraction = ""] = value.split(".");
  if (fraction.length > 18) {
    throw new Error("GEN amounts may have at most 18 decimal places.");
  }
  return BigInt(whole) * 10n ** 18n + BigInt(fraction.padEnd(18, "0") || "0");
}

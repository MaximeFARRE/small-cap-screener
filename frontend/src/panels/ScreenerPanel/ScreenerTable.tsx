import * as React from "react";
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { MetricCell } from "@/components/MetricCell";
import { ScoreBadge } from "@/components/ScoreBadge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { CompanyRow } from "@/hooks";
import { cn } from "@/lib/utils";

type SortDirection = "asc" | "desc";
type SortableColumnKey =
  | "ticker"
  | "name"
  | "total_score"
  | "sector"
  | "market_cap"
  | "pe_ratio"
  | "ev_ebitda"
  | "roe"
  | "revenue_growth"
  | "net_debt_to_ebitda";

interface SortState {
  key: SortableColumnKey;
  direction: SortDirection;
}

interface ScreenerTableProps {
  rows: CompanyRow[];
  activeTicker: string | null;
  onSelectTicker: (ticker: string | null) => void;
}

const DEFAULT_SORT: SortState = {
  key: "total_score",
  direction: "desc",
};

const COLUMN_LABELS: Record<SortableColumnKey, string> = {
  ticker: "Ticker",
  name: "Name",
  total_score: "Score",
  sector: "Sector",
  market_cap: "Market Cap",
  pe_ratio: "P/E",
  ev_ebitda: "EV/EBITDA",
  roe: "ROE",
  revenue_growth: "Rev Growth",
  net_debt_to_ebitda: "Net Debt/EBITDA",
};

function sortRows(rows: CompanyRow[], sort: SortState): CompanyRow[] {
  const sorted = [...rows];
  sorted.sort((left, right) => {
    const leftValue = left[sort.key];
    const rightValue = right[sort.key];

    if (leftValue === null && rightValue === null) {
      return 0;
    }
    if (leftValue === null) {
      return 1;
    }
    if (rightValue === null) {
      return -1;
    }

    if (typeof leftValue === "number" && typeof rightValue === "number") {
      return sort.direction === "asc" ? leftValue - rightValue : rightValue - leftValue;
    }

    const leftText = String(leftValue).toLowerCase();
    const rightText = String(rightValue).toLowerCase();
    if (leftText < rightText) {
      return sort.direction === "asc" ? -1 : 1;
    }
    if (leftText > rightText) {
      return sort.direction === "asc" ? 1 : -1;
    }
    return 0;
  });
  return sorted;
}

function SortIcon({ state, column }: { state: SortState; column: SortableColumnKey }) {
  if (state.key !== column) {
    return <ArrowUpDown className="h-3 w-3" />;
  }
  return state.direction === "asc" ? (
    <ArrowUp className="h-3 w-3" />
  ) : (
    <ArrowDown className="h-3 w-3" />
  );
}

export function ScreenerTable({ rows, activeTicker, onSelectTicker }: ScreenerTableProps) {
  const [sortState, setSortState] = React.useState<SortState>(DEFAULT_SORT);
  const sortedRows = React.useMemo(() => sortRows(rows, sortState), [rows, sortState]);

  const handleSort = (column: SortableColumnKey) => {
    setSortState((current) => {
      if (current.key === column) {
        return {
          key: column,
          direction: current.direction === "asc" ? "desc" : "asc",
        };
      }
      return {
        key: column,
        direction: column === "name" || column === "ticker" || column === "sector" ? "asc" : "desc",
      };
    });
  };

  return (
    <Table className="table-fixed">
      <TableHeader>
        <TableRow>
          {(Object.keys(COLUMN_LABELS) as SortableColumnKey[]).map((column) => (
            <TableHead key={column}>
              <button
                type="button"
                className="inline-flex items-center gap-1 font-mono text-[11px] uppercase"
                onClick={() => handleSort(column)}
              >
                {COLUMN_LABELS[column]}
                <SortIcon state={sortState} column={column} />
              </button>
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {sortedRows.length === 0 ? (
          <TableRow>
            <TableCell colSpan={10} className="py-6 text-center font-mono text-sm text-[var(--color-text-muted)]">
              No companies match current filters.
            </TableCell>
          </TableRow>
        ) : (
          sortedRows.map((row) => {
            const ticker = row.ticker;
            const isActive = ticker !== null && ticker === activeTicker;

            return (
              <TableRow
                key={row.company_id}
                className={cn(
                  "cursor-pointer hover:bg-[var(--color-bg-elevated)]",
                  isActive && "bg-[var(--color-accent)]/15",
                )}
                onClick={() => onSelectTicker(ticker)}
              >
                <TableCell className="font-mono text-xs text-[var(--color-text-primary)]">
                  {ticker ?? "—"}
                </TableCell>
                <TableCell className="truncate text-xs text-[var(--color-text-primary)]">
                  {row.name}
                </TableCell>
                <TableCell>
                  <ScoreBadge score={row.total_score} />
                </TableCell>
                <TableCell className="text-xs text-[var(--color-text-muted)]">
                  {row.sector ?? "—"}
                </TableCell>
                <TableCell>
                  <MetricCell value={row.market_cap} type="market_cap" format="currency" />
                </TableCell>
                <TableCell>
                  <MetricCell value={row.pe_ratio} type="pe_ratio" format="ratio" />
                </TableCell>
                <TableCell>
                  <MetricCell value={row.ev_ebitda} type="ev_ebitda" format="ratio" />
                </TableCell>
                <TableCell>
                  <MetricCell value={row.roe} type="roe" format="percent" />
                </TableCell>
                <TableCell>
                  <MetricCell value={row.revenue_growth} type="revenue_growth" format="percent" />
                </TableCell>
                <TableCell>
                  <MetricCell value={row.net_debt_to_ebitda} type="net_debt_to_ebitda" format="ratio" />
                </TableCell>
              </TableRow>
            );
          })
        )}
      </TableBody>
    </Table>
  );
}

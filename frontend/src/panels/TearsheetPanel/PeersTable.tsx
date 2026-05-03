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
import type { PeerComparison } from "@/hooks";
import { cn } from "@/lib/utils";

interface PeersTableProps {
  peers: PeerComparison;
  activeTicker: string | null;
}

const PEER_COLUMN_WIDTH_CLASSES: string[] = [
  "w-[92px]",
  "w-[260px]",
  "w-[80px]",
  "w-[110px]",
  "w-[96px]",
  "w-[130px]",
  "w-[100px]",
  "w-[120px]",
  "w-[90px]",
  "w-[120px]",
  "w-[155px]",
];

export function PeersTable({ peers, activeTicker }: PeersTableProps) {
  const rankedRows = peers.peer_rows.filter((row) => row.peer_rank !== null);
  const bestRank = rankedRows.length > 0 ? Math.min(...rankedRows.map((row) => row.peer_rank ?? Number.MAX_VALUE)) : null;
  const worstRank = rankedRows.length > 0 ? Math.max(...rankedRows.map((row) => row.peer_rank ?? Number.MIN_VALUE)) : null;
  const percentileMetrics = peers.metrics
    .filter((metric) => metric.percentile_rank !== null)
    .slice(0, 4);

  return (
    <section className="space-y-3 p-4">
      <div className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-2">
        <p className="mb-1 font-mono text-xs uppercase text-[var(--color-text-muted)]">
          Percentile ranks
        </p>
        <div className="flex flex-wrap gap-2">
          {percentileMetrics.length === 0 ? (
            <span className="font-mono text-xs text-[var(--color-text-muted)]">No percentile data.</span>
          ) : (
            percentileMetrics.map((metric) => (
              <span
                key={metric.key}
                className="rounded-sm border border-[var(--color-border)] px-2 py-1 font-mono text-xs text-[var(--color-text-primary)]"
              >
                {metric.label}: {Math.round(metric.percentile_rank ?? 0)}th percentile
              </span>
            ))
          )}
        </div>
      </div>

      <Table className="min-w-[1163px] table-fixed">
        <colgroup>
          {PEER_COLUMN_WIDTH_CLASSES.map((widthClassName, index) => (
            <col key={index} className={widthClassName} />
          ))}
        </colgroup>
        <TableHeader>
          <TableRow>
            <TableHead>Ticker</TableHead>
            <TableHead>Name</TableHead>
            <TableHead>Rank</TableHead>
            <TableHead>Percentile</TableHead>
            <TableHead>Score</TableHead>
            <TableHead>Market Cap</TableHead>
            <TableHead>P/E</TableHead>
            <TableHead>EV/EBITDA</TableHead>
            <TableHead>ROE</TableHead>
            <TableHead>Rev Growth</TableHead>
            <TableHead>Net Debt/EBITDA</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {peers.peer_rows.map((row) => {
            const isActive = row.ticker !== null && row.ticker === activeTicker;
            const isBest = bestRank !== null && row.peer_rank === bestRank;
            const isWorst = worstRank !== null && row.peer_rank === worstRank;
            return (
              <TableRow
                key={row.company_id}
                className={cn(
                  isActive && "bg-[var(--color-accent)]/15",
                  isBest && "bg-[var(--color-positive)]/10",
                  isWorst && "bg-[var(--color-negative)]/10",
                )}
              >
                <TableCell className="font-mono text-xs">{row.ticker ?? "—"}</TableCell>
                <TableCell className="truncate text-xs">{row.name}</TableCell>
                <TableCell className="font-mono text-xs">{row.peer_rank ?? "—"}</TableCell>
                <TableCell className="font-mono text-xs">
                  {row.score_percentile === null ? "—" : `${Math.round(row.score_percentile)}th`}
                </TableCell>
                <TableCell>
                  <ScoreBadge score={row.total_score} />
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
          })}
        </TableBody>
      </Table>
    </section>
  );
}

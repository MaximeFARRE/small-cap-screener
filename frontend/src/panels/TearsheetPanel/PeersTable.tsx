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

export function PeersTable({ peers, activeTicker }: PeersTableProps) {
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

      <Table className="table-fixed">
        <TableHeader>
          <TableRow>
            <TableHead>Ticker</TableHead>
            <TableHead>Name</TableHead>
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
            return (
              <TableRow
                key={row.company_id}
                className={cn(isActive && "bg-[var(--color-accent)]/15")}
              >
                <TableCell className="font-mono text-xs">{row.ticker ?? "—"}</TableCell>
                <TableCell className="text-xs">{row.name}</TableCell>
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

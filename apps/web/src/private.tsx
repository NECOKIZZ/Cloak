import { useEffect, useRef, useState } from "react";
import { formatEther, isAddress, parseEther, type Address, type Hex } from "viem";
import {
  CloakPrivate,
  cloakFactoryAbi,
  loadProver,
  privateRouterAbi,
  relayerSubmitter,
  splitStandard,
  walletSubmitter,
  type AuctionState,
  type Prover,
  type Wallet,
} from "@cloak/sdk";
import { BATCHER, FACTORY, RELAYER_URL, ROUTER, ROUTER_BLOCK, txLink } from "./config";
import { hype, short, tokens } from "./format";
import { publicClient } from "./wallet";

const ZERO = "0x0000000000000000000000000000000000000000";
let proverPromise: Promise<Prover> | null = null;
const getProver = () => (proverPromise ??= loadProver("/circuits"));

const errMsg = (e: unknown) => {
  const x = e as { shortMessage?: string; message?: string };
  return x.shortMessage ?? x.message ?? String(e);
};

type Tab = "shield" | "buy" | "sell" | "send" | "withdraw";

export function PrivateCard({ s, wallet }: { s: AuctionState; wallet: Wallet | null }) {
  const [pool, setPool] = useState<Address | null | undefined>(undefined);
  const [priv, setPriv] = useState<CloakPrivate | null>(null);
  const [bal, setBal] = useState<{ hype: bigint; tok: bigint } | null>(null);
  const [tab, setTab] = useState<Tab>("shield");
  const [amt, setAmt] = useState("0.001");
  const [to, setTo] = useState("");
  const [quote, setQuote] = useState<bigint>(0n);
  const [mode, setMode] = useState<"batch" | "instant">(BATCHER ? "batch" : "instant");
  const [sendAsset, setSendAsset] = useState<"hype" | "token">("hype");
  const [myAddr, setMyAddr] = useState("");
  const [round, setRound] = useState<{ endsAt: number; round: bigint } | null>(null);
  const [now, setNow] = useState(Date.now() / 1000);
  const [busy, setBusy] = useState("");
  const [msg, setMsg] = useState<{ ok?: string; tx?: Hex; err?: string }>({});
  const syncing = useRef(false);

  // does this launch have a private market yet?
  useEffect(() => {
    if (!ROUTER || !s.settled || s.pair === ZERO) return;
    publicClient
      .readContract({ address: ROUTER, abi: privateRouterAbi, functionName: "poolOf", args: [s.token] })
      .then((p) => setPool(p === ZERO ? null : p))
      .catch(() => setPool(null));
  }, [s.settled, s.token]);

  async function refresh(p = priv) {
    if (!p || syncing.current) return;
    syncing.current = true;
    try {
      const [h, t] = await Promise.all([p.balance(p.hypeMarket.pool), p.balance(p.market(s.token).pool)]);
      setBal({ hype: h, tok: t });
    } finally {
      syncing.current = false;
    }
  }

  useEffect(() => {
    if (!priv) return;
    const t = setInterval(() => refresh(), 8000);
    return () => clearInterval(t);
  }, [priv]);

  // batch round clock
  useEffect(() => {
    if (!priv || !BATCHER) return;
    const tick = () => priv.roundInfo().then(setRound).catch(() => {});
    tick();
    const t = setInterval(() => {
      setNow(Date.now() / 1000);
      if (round && Date.now() / 1000 > round.endsAt) tick();
    }, 1000);
    return () => clearInterval(t);
  }, [priv, round?.endsAt]);

  useEffect(() => {
    if (!priv || (tab !== "buy" && tab !== "sell")) return setQuote(0n);
    let alive = true;
    (async () => {
      try {
        const q = await priv.quote(s.token, tab, parseEther(amt || "0"));
        if (alive) setQuote(q);
      } catch {
        if (alive) setQuote(0n);
      }
    })();
    return () => {
      alive = false;
    };
  }, [priv, tab, amt]);

  if (!ROUTER || !s.settled || s.failed || s.pair === ZERO) return null;

  async function enable() {
    if (!wallet || !FACTORY) return;
    setBusy("enable");
    setMsg({});
    try {
      const n = await publicClient.readContract({ address: FACTORY, abi: cloakFactoryAbi, functionName: "launchesCount" });
      let idx = -1n;
      for (let i = n - 1n; i >= 0n; i--) {
        const [auction] = await publicClient.readContract({ address: FACTORY, abi: cloakFactoryAbi, functionName: "launches", args: [i] });
        if (auction.toLowerCase() === s.address.toLowerCase()) {
          idx = i;
          break;
        }
      }
      if (idx < 0n) throw new Error("launch not found in factory");
      const h = await wallet.writeContract({ address: ROUTER!, abi: privateRouterAbi, functionName: "createPool", args: [idx] });
      await publicClient.waitForTransactionReceipt({ hash: h });
      const p = await publicClient.readContract({ address: ROUTER!, abi: privateRouterAbi, functionName: "poolOf", args: [s.token] });
      setPool(p);
    } catch (e) {
      setMsg({ err: errMsg(e) });
    } finally {
      setBusy("");
    }
  }

  async function unlock() {
    if (!wallet) return;
    setBusy("unlock");
    setMsg({});
    try {
      const keys = await CloakPrivate.keysFromWallet(wallet);
      const submit = RELAYER_URL ? relayerSubmitter(RELAYER_URL) : walletSubmitter(publicClient, wallet, ROUTER!);
      const p = new CloakPrivate(publicClient, ROUTER!, keys, getProver, submit, ROUTER_BLOCK, BATCHER);
      await p.loadMarkets();
      setPriv(p);
      setMyAddr(await p.address());
      getProver(); // start downloading the circuit in the background
      await refresh(p);
    } catch (e) {
      setMsg({ err: errMsg(e) });
    } finally {
      setBusy("");
    }
  }

  async function act() {
    if (!priv || !wallet) return;
    setMsg({});
    const a = parseEther(amt || "0");
    const status = (m: string) => setBusy(m);
    try {
      let tx: Hex;
      if (tab === "shield") {
        status("Depositing into your private balance…");
        tx = await priv.shieldHype(wallet, a);
        setMsg({ ok: `${amt} HYPE is now private.`, tx });
      } else if ((tab === "buy" || tab === "sell") && mode === "batch") {
        status("Loading the prover…");
        await getProver();
        const r = await priv.batch(s.token, tab, a, { onStatus: status });
        const rounds = [...new Set(r.orders.map((o) => o.round.toString()))];
        setMsg({
          ok: `${r.orders.length} standard-size ${tab} orders placed in round ${rounds.join(", ")}. They fill privately when the round settles${r.rest > 0n ? `; ${tab === "buy" ? hype(r.rest) + " HYPE" : tokens(r.rest) + " " + s.tokenSymbol} stays in your balance` : ""}.`,
          tx: r.orders[r.orders.length - 1]?.txHash,
        });
      } else if (tab === "buy") {
        status("Loading the prover…");
        await getProver();
        const r = await priv.buy(s.token, a, { onStatus: status });
        setMsg({ ok: `Bought ~${tokens(r.expectedOut)} ${s.tokenSymbol} privately.`, tx: r.txHash });
      } else if (tab === "sell") {
        status("Loading the prover…");
        await getProver();
        const r = await priv.sell(s.token, a, { onStatus: status });
        setMsg({ ok: `Sold ${amt} ${s.tokenSymbol} for ~${hype(r.expectedOut)} HYPE, privately.`, tx: r.txHash });
      } else if (tab === "send") {
        if (!to.startsWith("cloak:")) throw new Error("paste the recipient's cloak: address");
        status("Loading the prover…");
        await getProver();
        tx = await priv.send(sendAsset === "hype" ? priv.hypeMarket.token : s.token, to, a, status);
        setMsg({ ok: `Sent privately. Nobody else can see the amount, the sender or the recipient.`, tx });
      } else {
        if (!isAddress(to)) throw new Error("enter the address to send to (a fresh one keeps you unlinkable)");
        status("Loading the prover…");
        await getProver();
        tx = await priv.unshieldHype(to, a, status);
        setMsg({ ok: `${amt} HYPE sent to ${short(to)}.`, tx });
      }
      await refresh();
    } catch (e) {
      setMsg({ err: errMsg(e) });
    } finally {
      setBusy("");
    }
  }

  const labels: Record<Tab, string> = { shield: "Shield", buy: "Buy", sell: "Sell", send: "Send", withdraw: "Withdraw" };
  const tokenSide = tab === "sell" || (tab === "send" && sendAsset === "token");
  const unit = tokenSide ? s.tokenSymbol : "HYPE";
  const max = bal ? (tokenSide ? bal.tok : tab === "shield" ? undefined : bal.hype) : undefined;
  const isTrade = tab === "buy" || tab === "sell";
  const split = (() => {
    try {
      return splitStandard(parseEther(amt || "0"), 6);
    } catch {
      return { sizes: [] as bigint[], rest: 0n };
    }
  })();
  const fmtAmt = (x: bigint) => (tab === "sell" ? tokens(x) : hype(x));

  return (
    <div className="card private">
      <div className="card-head">
        <h3>Private trading</h3>
        <span className="pill sealed-p">● shielded</span>
      </div>
      {pool === undefined ? (
        <p className="mute small">Checking…</p>
      ) : pool === null ? (
        <>
          <p className="mute small">Turn on a shielded market for ${s.tokenSymbol}. Anyone can do it once, after settlement.</p>
          <button className="btn btn-ghost btn-block" disabled={!wallet || !!busy} onClick={enable}>
            {busy === "enable" ? "Creating private market…" : wallet ? "Enable private trading" : "Connect a wallet"}
          </button>
        </>
      ) : !priv ? (
        <>
          <p className="mute small">
            Buy and sell ${s.tokenSymbol} from a private balance. Trades are proven on your device and sent by a relayer, so your wallet never shows up on them.
          </p>
          <button className="btn btn-accent btn-block" disabled={!wallet || !!busy} onClick={unlock}>
            {busy === "unlock" ? "Sign in your wallet…" : wallet ? "Unlock private account" : "Connect a wallet"}
          </button>
          <p className="note">You sign one message (free, no transaction). Your private keys are derived from it on this device.</p>
        </>
      ) : (
        <>
          <div className="summary" style={{ marginTop: 0 }}>
            <div className="row"><span className="mute">Private HYPE</span><span className="mono">{bal ? hype(bal.hype) : "…"}</span></div>
            <div className="row"><span className="mute">Private {s.tokenSymbol}</span><span className="mono">{bal ? tokens(bal.tok) : "…"}</span></div>
            {myAddr && (
              <div className="row">
                <span className="mute">Your cloak address</span>
                <span className="link mono xs" title={myAddr} onClick={() => navigator.clipboard?.writeText(myAddr).catch(() => {})}>{myAddr.slice(0, 14)}…{myAddr.slice(-6)} ⧉</span>
              </div>
            )}
          </div>
          <div className="tabs">
            {(Object.keys(labels) as Tab[]).map((t) => (
              <button key={t} className={`tab ${tab === t ? "on" : ""}`} onClick={() => { setTab(t); setMsg({}); }}>{labels[t]}</button>
            ))}
          </div>
          {isTrade && BATCHER && (
            <div className="buckets" style={{ marginBottom: 12 }}>
              <button className={`bucket ${mode === "batch" ? "on" : ""}`} onClick={() => setMode("batch")}>Batch · hides size</button>
              <button className={`bucket ${mode === "instant" ? "on" : ""}`} onClick={() => setMode("instant")}>Instant</button>
            </div>
          )}
          {tab === "send" && (
            <div className="buckets" style={{ marginBottom: 12 }}>
              <button className={`bucket ${sendAsset === "hype" ? "on" : ""}`} onClick={() => setSendAsset("hype")}>HYPE</button>
              <button className={`bucket ${sendAsset === "token" ? "on" : ""}`} onClick={() => setSendAsset("token")}>{s.tokenSymbol}</button>
            </div>
          )}
          <div className="field">
            <label>
              <span>{tab === "shield" ? "Deposit HYPE from your wallet" : tab === "buy" ? "Spend private HYPE" : tab === "sell" ? `Sell private ${s.tokenSymbol}` : tab === "send" ? `Send private ${unit}` : "Withdraw private HYPE"}</span>
              {max !== undefined && <span className="link" onClick={() => setAmt(formatEther(max))}>max {tokenSide ? tokens(max) : hype(max)}</span>}
            </label>
            <input className="input" value={amt} onChange={(e) => setAmt(e.target.value)} inputMode="decimal" />
          </div>
          {(tab === "withdraw" || tab === "send") && (
            <div className="field">
              <label><span>{tab === "send" ? "Recipient cloak: address" : "To address"}</span><span>{tab === "send" ? "amount stays hidden" : "use a fresh one"}</span></label>
              <input className="input" value={to} onChange={(e) => setTo(e.target.value.trim())} placeholder={tab === "send" ? "cloak:…" : "0x…"} />
            </div>
          )}
          {isTrade && mode === "instant" && (
            <div className="summary">
              <div className="row"><span className="mute">You receive ≈</span><span className="mono">{tab === "buy" ? `${tokens(quote)} ${s.tokenSymbol}` : `${hype(quote)} HYPE`}</span></div>
              <div className="row"><span className="mute">On-chain sender</span><span>relayer, not you</span></div>
              <div className="row"><span className="mute">Trade size</span><span className="warn-t">visible on the pool</span></div>
            </div>
          )}
          {isTrade && mode === "batch" && (
            <div className="summary">
              <div className="row"><span className="mute">Orders</span><span className="mono">{split.sizes.length ? split.sizes.map(fmtAmt).join(" + ") : "—"}</span></div>
              {split.rest > 0n && <div className="row"><span className="mute">Stays private (not a standard size)</span><span className="mono">{fmtAmt(split.rest)}</span></div>}
              <div className="row"><span className="mute">Expected ≈</span><span className="mono">{tab === "buy" ? `${tokens(quote)} ${s.tokenSymbol}` : `${hype(quote)} HYPE`}</span></div>
              <div className="row"><span className="mute">Round settles in</span><span className="mono">{round ? `${Math.max(0, Math.ceil(round.endsAt - now))}s` : "…"}</span></div>
            </div>
          )}
          <button className="btn btn-accent btn-block" disabled={!!busy || !wallet} onClick={act}>
            {busy || (tab === "shield" ? "Shield HYPE" : isTrade && mode === "batch" ? `Place ${split.sizes.length || ""} sealed ${tab} order${split.sizes.length === 1 ? "" : "s"}` : tab === "buy" ? `Buy ${s.tokenSymbol} privately` : tab === "sell" ? `Sell ${s.tokenSymbol} privately` : tab === "send" ? "Send privately" : "Withdraw privately")}
          </button>
          {msg.err && <div className="err">{msg.err}</div>}
          {msg.ok && (
            <div className="okmsg">
              {msg.ok} {msg.tx && (txLink(msg.tx) ? <a href={txLink(msg.tx)} target="_blank" rel="noreferrer">view tx ↗</a> : <span className="mono faint">{short(msg.tx)}</span>)}
            </div>
          )}
          <p className="note">
            {tab === "shield"
              ? `Shielding is the one public step: your wallet deposits ${unit}. It goes to a one-time key, so it can't be linked to your trades.`
              : !RELAYER_URL
                ? "No relayer configured: your wallet will submit this itself (works, but not private)."
                : isTrade && mode === "batch"
                  ? "Batch mode: your amount is split into standard sizes everyone uses. At the end of the round, buys and sells cross at the mid-price and only the net touches the pool, so nobody can tell how much you traded."
                  : tab === "send"
                    ? "A transfer inside the vault: the chain sees that a private transaction happened, not who, to whom or how much."
                    : "The proof is generated on this device (~3 s). On-chain, the trade comes from the relayer and lands in the shielded pool."}
          </p>
        </>
      )}
      {pool === null && msg.err && <div className="err">{msg.err}</div>}
    </div>
  );
}

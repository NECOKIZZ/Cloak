import { useCallback, useEffect, useState } from "react";
import type { Address } from "viem";
import { Cloak, cloakAuctionAbi, drandRoundTime, type AuctionState, type Wallet } from "@cloak/sdk";
import { BidCard, CreateLaunch, DemandChart, FairLaunchCard, LaunchList, MyBids, TradeCard } from "./components";
import { PrivateCard } from "./private";
import { addrLink, chain, FACTORY, IS_LOCAL, KEEPER_URL } from "./config";
import { duration, hype, short, tokens } from "./format";
import { connectBurner, connectInjected, publicClient, readCloak } from "./wallet";

type MyBids = Awaited<ReturnType<typeof readCloak.bidsOf>>;
const PHASES = [
  { k: "commit", label: "Sealed bidding" },
  { k: "reveal", label: "Auto-reveal" },
  { k: "settle", label: "Settle" },
  { k: "settled", label: "Trading" },
] as const;

function getQueryAuction(): Address | undefined {
  const a = new URLSearchParams(location.search).get("a");
  return a && /^0x[0-9a-fA-F]{40}$/.test(a) ? (a as Address) : undefined;
}

export function App() {
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [auction, setAuction] = useState<Address | undefined>(getQueryAuction());
  const [s, setS] = useState<AuctionState | null>(null);
  const [curve, setCurve] = useState<bigint[]>([]);
  const [mine, setMine] = useState<MyBids>([]);
  const [now, setNow] = useState(Date.now() / 1000);
  const [err, setErr] = useState("");
  const [keeper, setKeeper] = useState<{ keeper: string } | null>(null);
  const [settling, setSettling] = useState(false);
  const [revealing, setRevealing] = useState("");

  // default to the newest launch
  useEffect(() => {
    if (auction || !FACTORY) return;
    readCloak.listLaunches().then((l) => l.length && pick(l[l.length - 1].auction)).catch((e) => setErr(e.shortMessage ?? e.message));
  }, []);

  const pick = (a: Address) => {
    setAuction(a);
    setS(null);
    setMine([]);
    history.replaceState(null, "", `?a=${a}`);
  };

  const refresh = useCallback(async () => {
    if (!auction) return;
    try {
      const [st, c] = await Promise.all([
        readCloak.getAuction(auction),
        publicClient.readContract({ address: auction, abi: cloakAuctionAbi, functionName: "demandCurve" }),
      ]);
      setS(st);
      setCurve([...c]);
      if (wallet) setMine(await readCloak.bidsOf(auction, wallet.account.address));
      setErr("");
    } catch (e) {
      const x = e as { shortMessage?: string; message?: string };
      setErr(x.shortMessage ?? x.message ?? "failed to load launch");
    }
  }, [auction, wallet]);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 4000);
    return () => clearInterval(t);
  }, [refresh]);
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now() / 1000), 250);
    return () => clearInterval(t);
  }, []);
  useEffect(() => {
    if (!KEEPER_URL) return;
    fetch(KEEPER_URL).then((r) => r.json()).then(setKeeper).catch(() => {});
  }, []);

  async function connect(kind: "injected" | "burner") {
    try {
      setWallet(kind === "burner" ? await connectBurner() : await connectInjected());
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  async function settleNow() {
    if (!wallet || !s) return;
    setSettling(true);
    try {
      await new Cloak(publicClient, wallet).settle(s.address);
      await refresh();
    } catch (e) {
      setErr((e as { shortMessage?: string }).shortMessage ?? (e as Error).message);
    } finally {
      setSettling(false);
    }
  }

  async function revealAllNow() {
    if (!wallet || !s) return;
    setRevealing("Decrypting sealed bids with the drand beacon…");
    try {
      const r = await new Cloak(publicClient, wallet).revealAll(s.address, { log: (m) => setRevealing(m) });
      setRevealing(r.revealed ? `Opened ${r.revealed} sealed bids.` : "Nothing left to open.");
      await refresh();
    } catch (e) {
      setRevealing("");
      setErr((e as { shortMessage?: string }).shortMessage ?? (e as Error).message);
    }
  }

  const phaseIdx = s ? PHASES.findIndex((p) => p.k === s.phase) : -1;
  const target = s ? (s.phase === "commit" ? s.commitEnd : s.phase === "reveal" ? s.revealEnd : 0) : 0;

  return (
    <>
      <header className="wrap top">
        <div className="brand"><img src="/logo.svg" alt="" />Cloak</div>
        <div className="top-right">
          <span className="net"><span className="dot" />{chain.name}</span>
          {wallet ? (
            <span className="pill mono">{short(wallet.account.address)}</span>
          ) : (
            <>
              {IS_LOCAL && <button className="btn btn-ghost btn-sm" onClick={() => connect("burner")}>Dev wallet</button>}
              <button className="btn btn-primary btn-sm" onClick={() => connect("injected")}>Connect</button>
            </>
          )}
        </div>
      </header>

      <main className="wrap">
        <section className="hero">
          <div>
            <span className="eyebrow"><span className="dot" />Sealed-bid launch · Elysium</span>
            <h1>
              {s ? <>{s.tokenName} <span className="faint">${s.tokenSymbol}</span></> : <>Launches nobody can <em>snipe</em>.</>}
            </h1>
            <p>
              Bids stay sealed until bidding closes, hidden even from the sequencer. Every winner pays <b>one clearing price</b>, and
              liquidity is seeded at that price and locked by the contract. Being first, fast or paying more gas gains you nothing.
            </p>
          </div>
          {s && (
            <div className="phase-card">
              <div className="phases">
                {PHASES.map((p, i) => (
                  <div key={p.k} className={`ph ${i === phaseIdx ? "on" : i < phaseIdx ? "done" : ""}`}>{p.label}</div>
                ))}
              </div>
              {s.phase === "commit" || s.phase === "reveal" ? (
                <>
                  <div className="small mute">{s.phase === "commit" ? "Bidding closes in" : "Reveal window closes in"}</div>
                  <div className="countdown tnum">{duration(target - now)}</div>
                  {s.phase === "reveal" && <div className="xs mute">drand round #{s.tlockRound} published · keepers are opening sealed bids ({s.reveals}/{s.commits})</div>}
                </>
              ) : s.phase === "settle" ? (
                <>
                  <div className="small mute">Reveal window closed. Anyone can settle.</div>
                  <button className="btn btn-accent" style={{ marginTop: 10 }} disabled={!wallet || settling} onClick={settleNow}>{settling ? "Settling…" : "Settle launch"}</button>
                </>
              ) : (
                <>
                  <div className="small mute">Cleared at</div>
                  <div className="countdown tnum">{hype(s.clearingPrice)} <span className="small mute">HYPE / {s.tokenSymbol}</span></div>
                </>
              )}
            </div>
          )}
        </section>

        {!FACTORY && !auction && (
          <div className="card" style={{ marginBottom: 20 }}>
            <h3>Not configured</h3>
            <p className="mute">Set <span className="mono">VITE_FACTORY</span> (and optionally <span className="mono">VITE_RPC_URL</span>) or open a launch with <span className="mono">?a=0x…</span>.</p>
          </div>
        )}
        {err && <div className="err" style={{ marginBottom: 16 }}>{err}</div>}

        {s && (
          <div className="stats" style={{ marginBottom: 20 }}>
            <div className="stat"><div className="k">For sale</div><div className="v">{tokens(s.saleSupply)}</div></div>
            <div className="stat"><div className="k">Sealed bids</div><div className="v">{s.commits}</div></div>
            <div className="stat"><div className="k">Locked deposits</div><div className="v">{hype(s.totalDeposits)} <span className="small mute">HYPE</span></div></div>
            <div className="stat">
              <div className="k">Demand</div>
              <div className="v">{s.phase === "commit" ? <span className="sealed" style={{ width: 90, height: 20 }} /> : tokens(s.totalDemand)}</div>
            </div>
          </div>
        )}

        <div className="grid">
          <div className="col">
            {s && <DemandChart s={s} curve={curve} />}
            {s && <FairLaunchCard s={s} />}
            {s && <MyBids s={s} wallet={wallet} bids={mine} onDone={refresh} />}
          </div>
          <div className="col">
            {s?.phase === "commit" && <BidCard s={s} wallet={wallet} onDone={refresh} />}
            {s && <PrivateCard s={s} wallet={wallet} />}
            {s && <TradeCard s={s} wallet={wallet} />}
            {s && s.phase !== "commit" && !s.settled && (
              <div className="card">
                <h3>Bidding is closed</h3>
                <p className="mute small">
                  Sealed bids open themselves: the drand beacon publishes round #{s.tlockRound}, and any keeper decrypts and reveals every bid.
                  {keeper && <> Keeper <span className="mono">{short(keeper.keeper)}</span> is online.</>}
                </p>
                {s.phase === "reveal" && s.reveals < s.commits && now >= drandRoundTime(s.tlockRound) && (
                  <>
                    <p className="mute small">No keeper needed: you can open every bid yourself. It only needs the public beacon.</p>
                    <button className="btn btn-ghost btn-block" disabled={!wallet || (!!revealing && !revealing.startsWith("Opened") && !revealing.startsWith("Nothing"))} onClick={revealAllNow}>
                      {wallet ? "Open all sealed bids" : "Connect a wallet to open bids"}
                    </button>
                  </>
                )}
                {revealing && <div className="okmsg">{revealing}</div>}
              </div>
            )}
            <CreateLaunch wallet={wallet} onCreated={pick} />
            <LaunchList current={auction} onPick={pick} />
          </div>
        </div>

        <section className="why">
          <div className="card"><span className="num">01</span><h3>Sequencer-proof</h3><p>Elysium has one sequencer that orders by priority fee. During bidding it sees only a hash and a timelock ciphertext. Paying for ordering, or Timeboost later, buys nothing.</p></div>
          <div className="card"><span className="num">02</span><h3>Reveals itself</h3><p>Bids are encrypted to a drand round that fires when bidding ends. After that anyone can open them. There is no "come back and reveal", and no bids get stranded.</p></div>
          <div className="card"><span className="num">03</span><h3>One price, locked liquidity</h3><p>Everyone who wins pays the same clearing price. The pool opens at exactly that price, with its LP burned or time-locked by the contract.</p></div>
        </section>
      </main>

      <footer className="wrap foot">
        <span>Cloak: sealed-bid launches for Elysium · built for Ascend</span>
        <span>
          {FACTORY && (addrLink(FACTORY) ? <a href={addrLink(FACTORY)} target="_blank" rel="noreferrer">factory {short(FACTORY)} ↗</a> : <span className="mono">factory {short(FACTORY)}</span>)}
          {" · "}
          <a href="https://github.com/NECOKIZZ/cloak" target="_blank" rel="noreferrer">github</a>
        </span>
      </footer>
    </>
  );
}

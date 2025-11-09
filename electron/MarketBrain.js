import React, { useState, useEffect } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  LineChart, Line, BarChart, Bar,
  XAxis, YAxis, Tooltip, CartesianGrid, Legend, ResponsiveContainer
} from "recharts";

const CHAINS = ["ETH", "SOL", "MATIC", "POL", "BNB", "AVAX"];

export default function MarketBrain() {
  const [symbol, setSymbol] = useState("ETH");
  const [data, setData] = useState([]);
  const [insight, setInsight] = useState("");
  const [loading, setLoading] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await fetch(
        `http://127.0.0.1:5001/api/marketbrain?symbols=${symbol}&startDate=2025-09-09&endDate=2025-10-09`
      );
      const json = await res.json();

      // 🧠 Adaptar estructura: si viene analytics, usarlo directamente
      if (json.analytics && Array.isArray(json.analytics)) {
        setData(json.analytics);
        if (json.analytics[0]?.insights) setInsight(json.analytics[0].insights);
      } else if (json.results) {
        const arr = Object.entries(json.results).map(([sym, content]) => ({
          symbol: sym,
          activeAddresses: content.stats?.active_addresses || 0,
          totalTransactions: content.stats?.total_transactions || 0,
          txFeesUSD: content.stats?.tx_fees_usd || 0,
          priceUSD: content.stats?.price_avg,
          insights: content.insights || "",
          timestamp: content.timestamp
        }));
        setData(arr);
        if (arr[0]?.insights) setInsight(arr[0].insights);
      } else {
        setData([]);
        setInsight("No data available");
      }
    } catch (err) {
      console.error("Fetch error", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [symbol]);

  return (
    <div className="p-4 space-y-4">
      {/* Selector y botón */}
      <Card>
        <CardContent className="flex gap-4 items-center">
          <select
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="border rounded p-2"
          >
            {CHAINS.map((c) => (
              <option key={c} value={c}>
                {c.toUpperCase()}
              </option>
            ))}
          </select>
          <Button onClick={fetchData} disabled={loading}>
            {loading ? "Loading..." : "Refresh"}
          </Button>
        </CardContent>
      </Card>

      {/* Insights */}
      <Card>
        <CardContent>
          <h2 className="text-xl font-bold mb-2">AI Insights</h2>
          <p className="text-gray-300 whitespace-pre-line">
            {insight || "No insights available."}
          </p>
        </CardContent>
      </Card>

      {/* Tabla */}
      <Card>
        <CardContent>
          <h2 className="text-xl font-bold mb-2">Analytics Overview</h2>
          <div className="overflow-x-auto">
            <table className="table-auto border-collapse border w-full text-sm">
              <thead>
                <tr>
                  <th className="border px-2">Symbol</th>
                  <th className="border px-2">Date</th>
                  <th className="border px-2">Active Addresses</th>
                  <th className="border px-2">Transactions</th>
                  <th className="border px-2">Fees (USD)</th>
                  <th className="border px-2">Price (USD)</th>
                </tr>
              </thead>
              <tbody>
                {data.map((row, idx) => (
                  <tr key={idx}>
                    <td className="border px-2">{row.symbol}</td>
                    <td className="border px-2">
                      {row.timestamp
                        ? new Date(row.timestamp).toLocaleString()
                        : "-"}
                    </td>
                    <td className="border px-2">{row.activeAddresses ?? "-"}</td>
                    <td className="border px-2">{row.totalTransactions ?? "-"}</td>
                    <td className="border px-2">{row.txFeesUSD ?? "-"}</td>
                    <td className="border px-2">{row.priceUSD ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Gráfico de actividad */}
      <Card>
        <CardContent>
          <h2 className="text-xl font-bold mb-2">Transactions & Fees</h2>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="symbol" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey="totalTransactions"
                stroke="#8884d8"
                name="Transactions"
              />
              <Line
                type="monotone"
                dataKey="txFeesUSD"
                stroke="#82ca9d"
                name="Fees (USD)"
              />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Gráfico de direcciones activas */}
      <Card>
        <CardContent>
          <h2 className="text-xl font-bold mb-2">Active Addresses</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="symbol" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar
                dataKey="activeAddresses"
                fill="#8884d8"
                name="Active Addresses"
              />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
}
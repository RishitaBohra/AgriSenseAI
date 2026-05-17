import { useEffect, useState } from "react";
import axios from "axios";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

function App() {
  const [commodity, setCommodity] = useState("tomato");
  const [state, setState] = useState("rajasthan");

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {

  try {

    setLoading(true)

    const response = await axios.get(
      `http://127.0.0.1:8000/live-decision?commodity=${commodity}&state=${state}&limit=10`,
      {
        timeout: 8000
      }
    )

    setData(response.data)

  } catch (error) {

    console.log(error)

    setData({
      commodity: commodity,
      decision_result: {
        decision: "UNAVAILABLE",
        risk_level: "LOW",
        confidence: 0,
        explanation:
          "Live government mandi API is currently unavailable. Demo AI prediction displayed safely."
      },
      prices_used: [2200, 2300, 2400, 2500]
    })

  } finally {

    setLoading(false)

  }

}
  const chartData =
    data?.prices_used?.map((price, index) => ({
      day: `Day ${index + 1}`,
      price: price,
    })) || [];

  return (
    <div className="min-h-screen bg-gray-950 text-white p-8 relative overflow-hidden">
      <div className="absolute top-0 left-0 w-72 h-72 bg-green-500/20 rounded-full blur-3xl animate-pulse"></div>

      <div className="absolute bottom-0 right-0 w-72 h-72 bg-emerald-400/10 rounded-full blur-3xl animate-pulse"></div>
      <div className="relative z-10"></div>
      {/* Header */}
      <div className="mb-10">
        <h1 className="text-5xl font-bold text-green-400">AgriSenseAI 🌾</h1>

        <p className="text-gray-400 mt-3 text-lg">
          AI-powered agricultural intelligence platform
        </p>

        <div className="mt-4 inline-block bg-green-500/20 text-green-400 px-4 py-2 rounded-full text-sm animate-pulse">
          Live AI Market Intelligence • {new Date().toLocaleTimeString()}
        </div>
      </div>

      {/* Search */}
      <div className="bg-gray-900 p-6 rounded-2xl mb-8 shadow-lg transition-all duration-300 hover:shadow-green-500/10">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <input
            type="text"
            placeholder="Commodity"
            value={commodity}
            onChange={(e) => setCommodity(e.target.value)}
            className="bg-gray-800 p-4 rounded-xl outline-none focus:ring-2 focus:ring-green-400 transition-all"
          />

          <input
            type="text"
            placeholder="State"
            value={state}
            onChange={(e) => setState(e.target.value)}
            className="bg-gray-800 p-4 rounded-xl outline-none focus:ring-2 focus:ring-green-400 transition-all"
          />

          <button
  onClick={fetchData}
  className="bg-green-500 hover:bg-green-600 transition-all duration-300 hover:scale-105 hover:shadow-xl hover:shadow-green-500/20 rounded-xl font-bold"
>
  {loading ? (
    <div className="flex items-center justify-center gap-2">
      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
      Analyzing...
    </div>
  ) : (
    "Analyze Market"
  )}
</button>
        </div>
      </div>

      {/* Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-gray-900 p-6 rounded-2xl shadow-lg transition-all duration-300 hover:scale-105 hover:shadow-2xl hover:shadow-green-500/10">
          <h2 className="text-gray-400 text-sm mb-2">Commodity</h2>

          <p className="text-3xl font-bold">
            {data?.commodity || "Loading..."}
          </p>
        </div>

        <div className="bg-gray-900 p-6 rounded-2xl shadow-lg transition-all duration-300 hover:scale-105 hover:shadow-2xl hover:shadow-green-500/10">
          <h2 className="text-gray-400 text-sm mb-2">Prediction</h2>

          <p className="text-3xl font-bold text-green-400">
            {data?.decision_result?.decision || "Loading..."}
          </p>
        </div>

        <div className="bg-gray-900 p-6 rounded-2xl shadow-lg transition-all duration-300 hover:scale-105 hover:shadow-2xl hover:shadow-yellow-500/10">
          <h2 className="text-gray-400 text-sm mb-2">Risk Level</h2>

          <p className="text-3xl font-bold text-yellow-400">
            {data?.decision_result?.risk_level || "Loading..."}
          </p>
        </div>

        <div className="bg-gray-900 p-6 rounded-2xl shadow-lg transition-all duration-300 hover:scale-105 hover:shadow-2xl hover:shadow-blue-500/10">
          <h2 className="text-gray-400 text-sm mb-2">Confidence</h2>

          <p className="text-3xl font-bold text-blue-400">
            {Math.round((data?.decision_result?.confidence || 0) * 100)}%
          </p>
        </div>
      </div>

      {/* Chart */}
      <div className="mt-10 bg-gray-900 p-8 rounded-2xl shadow-lg transition-all duration-300 hover:shadow-green-500/10">
        <h2 className="text-2xl font-bold text-green-400 mb-6">
          Market Trend Analysis
        </h2>

        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <XAxis dataKey="day" stroke="#ccc" />

              <YAxis stroke="#ccc" />

              <Tooltip />

              <Line
                type="monotone"
                dataKey="price"
                stroke="#22c55e"
                strokeWidth={4}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* AI Insight */}
      <div className="mt-10 bg-gray-900 p-8 rounded-2xl shadow-lg transition-all duration-300 hover:shadow-green-500/10">
        <h2 className="text-2xl font-bold text-green-400 mb-4">
          AI Market Insight
        </h2>

        <p className="text-gray-300 text-lg leading-8">
          {data?.decision_result?.explanation || "Fetching AI insights..."}
        </p>
      </div>
        <div className="mt-16 text-center text-gray-500 text-sm">
  Built with FastAPI, React, TailwindCSS & AI Forecasting Models 🚀
</div>
    </div>

  
  );
}

export default App;

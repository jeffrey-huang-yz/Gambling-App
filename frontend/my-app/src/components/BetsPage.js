import React from 'react';

const BetsPage = () => {
  const bets = [
    { id: 1, match: "Team A vs Team B", amount: "$50", odds: "2.5", status: "Active" },
    { id: 2, match: "Team C vs Team D", amount: "$25", odds: "1.8", status: "Won" },
    { id: 3, match: "Team E vs Team F", amount: "$100", odds: "3.2", status: "Lost" },
    { id: 4, match: "Team G vs Team H", amount: "$75", odds: "2.1", status: "Active" }
  ];

  const getStatusColor = (status) => {
    switch(status) {
      case 'Won': return 'bg-green-100 text-green-800';
      case 'Lost': return 'bg-red-100 text-red-800';
      case 'Active': return 'bg-blue-100 text-blue-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold text-gray-800 mb-6">My Bets</h1>
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-2xl font-semibold text-gray-700">Betting History</h2>
            <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors">
              Place New Bet
            </button>
          </div>
          <div className="space-y-3">
            {bets.map((bet) => (
              <div key={bet.id} className="p-4 border rounded-lg hover:shadow-md transition-shadow">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="font-semibold text-gray-800">{bet.match}</h3>
                    <div className="flex space-x-4 mt-2 text-sm text-gray-600">
                      <span>Amount: <span className="font-medium">{bet.amount}</span></span>
                      <span>Odds: <span className="font-medium">{bet.odds}</span></span>
                    </div>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(bet.status)}`}>
                    {bet.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default BetsPage;
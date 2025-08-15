import React from 'react';

const RankPage = () => {
  const rankings = [
    { rank: 1, name: "Player One", winnings: "$2,450" },
    { rank: 2, name: "Player Two", winnings: "$2,380" },
    { rank: 3, name: "Player Three", winnings: "$2,320" },
    { rank: 4, name: "Player Four", winnings: "$2,290" },
    { rank: 5, name: "Player Five", winnings: "$2,250" }
  ];

  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold text-gray-800 mb-6">Leaderboard</h1>
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-2xl font-semibold text-gray-700 mb-4">Top Bettors</h2>
          <div className="space-y-3">
            {rankings.map((player) => (
              <div key={player.rank} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                <div className="flex items-center">
                  <span className="text-2xl font-bold text-blue-600 w-12">#{player.rank}</span>
                  <span className="text-lg font-medium text-gray-800">{player.name}</span>
                </div>
                <span className="text-xl font-semibold text-green-600">{player.winnings}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default RankPage;
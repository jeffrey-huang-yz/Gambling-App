import React, { useState } from 'react';
import { sportsData } from '../data/sportsData';

const HomePage = ({ addToBetSlip, betSlipOpen, setBetSlipOpen, betSlip, updateBetAmount, removeBet, clearBetSlip, onPlaceBets }) => {
  const [selectedSport, setSelectedSport] = useState('nfl');

  const handleBetClick = (bet) => {
    // Check if bet is already in slip
    const existingBet = betSlip.find(existing => existing.id === bet.id);
    
    if (existingBet) {
      // Remove bet if it already exists
      removeBet(bet.id);
    } else {
      // Add bet if it doesn't exist
      addToBetSlip(bet);
      setBetSlipOpen(true);
    }
  };

  return (
    <div className="flex">
      {/* Main Content */}
      <div className={`flex-1 transition-all duration-300 ${betSlipOpen ? 'mr-96' : ''}`}>
        <div className="min-h-screen bg-gray-50">
          {/* Hero Section */}
          

          {/* Sports Navigation */}
          <div className="bg-white shadow-sm border-b">
            <div className="max-w-7xl mx-auto px-4">
              <div className="flex space-x-8 py-4">
                {Object.entries(sportsData).map(([key, sport]) => (
                  <button
                    key={key}
                    onClick={() => setSelectedSport(key)}
                    className={`flex items-center space-x-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                      selectedSport === key
                        ? 'bg-blue-100 text-blue-700'
                        : 'text-gray-600 hover:text-blue-600 hover:bg-gray-100'
                    }`}
                  >
                    <span className="text-2xl">{sport.icon}</span>
                    <span>{sport.name}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Games Section */}
          <div className="max-w-7xl mx-auto px-4 py-8">
            <h2 className="text-2xl font-bold text-gray-800 mb-6">
              {sportsData[selectedSport].name} Games
            </h2>
            
            <div className="space-y-4">
              {sportsData[selectedSport].games.map((game) => (
                <div key={game.id} className="bg-white rounded-lg shadow-md p-6">
                  <div className="flex justify-between items-center mb-4">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-800">
                        {game.team1} vs {game.team2}
                      </h3>
                      <p className="text-gray-600">{game.time}</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    {/* Spread */}
                    <div className="border rounded-lg p-4">
                      <h4 className="font-semibold text-gray-700 mb-2 text-center">Spread</h4>
                      <div className="space-y-2">
                        <button
                          onClick={() => handleBetClick({
                            id: `${game.id}-spread1`,
                            game: `${game.team1} vs ${game.team2}`,
                            type: 'Spread',
                            selection: `${game.spread1.team} ${game.spread1.line}`,
                            odds: game.spread1.odds,
                            team: game.team1
                          })}
                          className={`w-full border rounded p-2 text-sm transition-colors ${
                            betSlip.find(bet => bet.id === `${game.id}-spread1`)
                              ? 'bg-blue-100 border-blue-500 text-blue-700'
                              : 'bg-gray-50 hover:bg-blue-50 border-gray-200 hover:border-blue-300'
                          }`}
                        >
                          <div className="font-medium">{game.spread1.team} {game.spread1.line}</div>
                          <div className="text-gray-600">{game.spread1.odds}</div>
                        </button>
                        <button
                          onClick={() => handleBetClick({
                            id: `${game.id}-spread2`,
                            game: `${game.team1} vs ${game.team2}`,
                            type: 'Spread',
                            selection: `${game.spread2.team} ${game.spread2.line}`,
                            odds: game.spread2.odds,
                            team: game.team2
                          })}
                          className={`w-full border rounded p-2 text-sm transition-colors ${
                            betSlip.find(bet => bet.id === `${game.id}-spread2`)
                              ? 'bg-blue-100 border-blue-500 text-blue-700'
                              : 'bg-gray-50 hover:bg-blue-50 border-gray-200 hover:border-blue-300'
                          }`}
                        >
                          <div className="font-medium">{game.spread2.team} {game.spread2.line}</div>
                          <div className="text-gray-600">{game.spread2.odds}</div>
                        </button>
                      </div>
                    </div>

                    {/* Moneyline */}
                    <div className="border rounded-lg p-4">
                      <h4 className="font-semibold text-gray-700 mb-2 text-center">Moneyline</h4>
                      <div className="space-y-2">
                        <button
                          onClick={() => handleBetClick({
                            id: `${game.id}-ml1`,
                            game: `${game.team1} vs ${game.team2}`,
                            type: 'Moneyline',
                            selection: game.moneyline1.team,
                            odds: game.moneyline1.odds,
                            team: game.team1
                          })}
                          className={`w-full border rounded p-2 text-sm transition-colors ${
                            betSlip.find(bet => bet.id === `${game.id}-ml1`)
                              ? 'bg-blue-100 border-blue-500 text-blue-700'
                              : 'bg-gray-50 hover:bg-blue-50 border-gray-200 hover:border-blue-300'
                          }`}
                        >
                          <div className="font-medium">{game.moneyline1.team}</div>
                          <div className="text-gray-600">{game.moneyline1.odds}</div>
                        </button>
                        <button
                          onClick={() => handleBetClick({
                            id: `${game.id}-ml2`,
                            game: `${game.team1} vs ${game.team2}`,
                            type: 'Moneyline',
                            selection: game.moneyline2.team,
                            odds: game.moneyline2.odds,
                            team: game.team2
                          })}
                          className={`w-full border rounded p-2 text-sm transition-colors ${
                            betSlip.find(bet => bet.id === `${game.id}-ml2`)
                              ? 'bg-blue-100 border-blue-500 text-blue-700'
                              : 'bg-gray-50 hover:bg-blue-50 border-gray-200 hover:border-blue-300'
                          }`}
                        >
                          <div className="font-medium">{game.moneyline2.team}</div>
                          <div className="text-gray-600">{game.moneyline2.odds}</div>
                        </button>
                      </div>
                    </div>

                    {/* Total */}
                    <div className="border rounded-lg p-4">
                      <h4 className="font-semibold text-gray-700 mb-2 text-center">Total</h4>
                      <div className="space-y-2">
                        <button
                          onClick={() => handleBetClick({
                            id: `${game.id}-over`,
                            game: `${game.team1} vs ${game.team2}`,
                            type: 'Total',
                            selection: `Over ${game.total.points}`,
                            odds: game.total.over,
                            team: 'Over'
                          })}
                          className={`w-full border rounded p-2 text-sm transition-colors ${
                            betSlip.find(bet => bet.id === `${game.id}-over`)
                              ? 'bg-blue-100 border-blue-500 text-blue-700'
                              : 'bg-gray-50 hover:bg-blue-50 border-gray-200 hover:border-blue-300'
                          }`}
                        >
                          <div className="font-medium">Over {game.total.points}</div>
                          <div className="text-gray-600">{game.total.over}</div>
                        </button>
                        <button
                          onClick={() => handleBetClick({
                            id: `${game.id}-under`,
                            game: `${game.team1} vs ${game.team2}`,
                            type: 'Total',
                            selection: `Under ${game.total.points}`,
                            odds: game.total.under,
                            team: 'Under'
                          })}
                          className={`w-full border rounded p-2 text-sm transition-colors ${
                            betSlip.find(bet => bet.id === `${game.id}-under`)
                              ? 'bg-blue-100 border-blue-500 text-blue-700'
                              : 'bg-gray-50 hover:bg-blue-50 border-gray-200 hover:border-blue-300'
                          }`}
                        >
                          <div className="font-medium">Under {game.total.points}</div>
                          <div className="text-gray-600">{game.total.under}</div>
                        </button>
                      </div>
                    </div>

                    {/* More Bets */}
                    <div className="border rounded-lg p-4">
                      <h4 className="font-semibold text-gray-700 mb-2 text-center">More Bets</h4>
                      <button className="w-full bg-blue-600 text-white rounded p-2 text-sm hover:bg-blue-700 transition-colors">
                        View All Markets
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
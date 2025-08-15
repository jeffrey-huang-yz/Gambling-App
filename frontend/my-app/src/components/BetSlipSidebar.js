import React, { useState } from 'react';

const BetSlipSidebar = ({ 
  isOpen, 
  onClose, 
  betSlip, 
  updateBetAmount, 
  removeBet, 
  clearBetSlip,
  onPlaceBets 
}) => {
  const [betType, setBetType] = useState('straight');

  const calculateOdds = (odds) => {
    const num = parseInt(odds.replace(/[+-]/, ''));
    if (odds.startsWith('+')) {
      return num / 100;
    } else {
      return 100 / num;
    }
  };

  const calculatePayout = (amount, odds) => {
    const multiplier = calculateOdds(odds);
    return (amount * multiplier).toFixed(2);
  };

  const calculateParlayOdds = () => {
    if (betSlip.length < 2) return 0;
    let totalMultiplier = 1;
    betSlip.forEach(bet => {
      if (bet.amount > 0) {
        totalMultiplier *= (1 + calculateOdds(bet.odds));
      }
    });
    return totalMultiplier;
  };

  const getTotalParlayPayout = () => {
    if (betSlip.length < 2) return 0;
    const totalAmount = betSlip.reduce((sum, bet) => sum + (bet.amount || 0), 0);
    const multiplier = calculateParlayOdds();
    return (totalAmount * multiplier).toFixed(2);
  };

  const hasValidBets = betSlip.some(bet => bet.amount > 0);

  if (!isOpen) return null;

  return (
    <>
      {/* Sidebar */}
      <div className="fixed right-0 top-0 h-full w-96 bg-white shadow-2xl border-l border-gray-200 z-50 overflow-y-auto">
        <div className="p-4">
          {/* Header */}
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold text-gray-800">Bet Slip</h2>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 text-2xl"
            >
              ×
            </button>
          </div>

          {betSlip.length === 0 ? (
            <div className="text-center py-8">
              <div className="text-4xl mb-2">🎯</div>
              <p className="text-gray-500">Your bet slip is empty</p>
            </div>
          ) : (
            <>
              {/* Clear All Button */}
              <div className="flex justify-end mb-4">
                <button
                  onClick={clearBetSlip}
                  className="text-red-600 hover:text-red-800 text-sm font-medium"
                >
                  Clear All
                </button>
              </div>

              {/* Bet Type Toggle */}
              {betSlip.length > 1 && (
                <div className="flex bg-gray-100 rounded-lg p-1 mb-4">
                  <button
                    onClick={() => setBetType('straight')}
                    className={`flex-1 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                      betType === 'straight'
                        ? 'bg-white text-blue-600 shadow-sm'
                        : 'text-gray-600'
                    }`}
                  >
                    Straight
                  </button>
                  <button
                    onClick={() => setBetType('parlay')}
                    className={`flex-1 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                      betType === 'parlay'
                        ? 'bg-white text-blue-600 shadow-sm'
                        : 'text-gray-600'
                    }`}
                  >
                    Parlay ({betSlip.length})
                  </button>
                </div>
              )}

              {/* Bet List */}
              <div className="space-y-3 mb-4">
                {betSlip.map((bet) => (
                  <div key={bet.id} className="border rounded-lg p-3 bg-gray-50">
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-800">{bet.selection}</p>
                        <p className="text-xs text-gray-600">{bet.game}</p>
                        <p className="text-xs font-medium text-green-600">{bet.odds}</p>
                      </div>
                      <button
                        onClick={() => removeBet(bet.id)}
                        className="text-red-500 hover:text-red-700 ml-2"
                      >
                        ×
                      </button>
                    </div>
                    
                    {betType === 'straight' && (
                      <div className="space-y-2">
                        <input
                          type="number"
                          value={bet.amount || ''}
                          onChange={(e) => updateBetAmount(bet.id, parseFloat(e.target.value) || 0)}
                          className="w-full border rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                          placeholder="Bet amount"
                        />
                        {bet.amount > 0 && (
                          <div className="text-xs text-gray-600">
                            To win: <span className="font-medium text-green-600">
                              ${calculatePayout(bet.amount, bet.odds)}
                            </span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Parlay Summary */}
              {betType === 'parlay' && betSlip.length > 1 && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
                  <h4 className="font-medium text-blue-800 mb-2">Parlay Bet</h4>
                  <div className="space-y-2">
                    <input
                      type="number"
                      onChange={(e) => {
                        const amount = parseFloat(e.target.value) || 0;
                        const perBet = amount / betSlip.length;
                        betSlip.forEach(bet => updateBetAmount(bet.id, perBet));
                      }}
                      className="w-full border rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                      placeholder="Total bet amount"
                    />
                    <div className="text-sm text-blue-700">
                      <div>Odds: +{((calculateParlayOdds() - 1) * 100).toFixed(0)}</div>
                      <div>Potential payout: <span className="font-medium">${getTotalParlayPayout()}</span></div>
                    </div>
                  </div>
                </div>
              )}

              {/* Place Bet Button */}
              <button
                onClick={() => {
                  if (hasValidBets) {
                    onPlaceBets(betSlip, betType);
                    onClose();
                  }
                }}
                disabled={!hasValidBets}
                className={`w-full py-3 rounded-lg font-semibold transition-colors ${
                  hasValidBets
                    ? 'bg-green-600 text-white hover:bg-green-700'
                    : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                }`}
              >
                Place {betType === 'parlay' ? 'Parlay' : 'Bet'}
              </button>
            </>
          )}
        </div>
      </div>
    </>
  );
};

export default BetSlipSidebar;
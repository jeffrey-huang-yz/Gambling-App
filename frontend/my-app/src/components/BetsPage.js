import React, { useState } from 'react';

const BetsPage = ({ betHistory }) => {
  const [filter, setFilter] = useState('all'); // 'all', 'active', 'settled'

  const filteredBets = betHistory.filter(bet => {
    if (filter === 'active') return bet.status === 'active';
    if (filter === 'settled') return bet.status === 'won' || bet.status === 'lost';
    return true;
  });

  const getStatusBadge = (status) => {
    const statusStyles = {
      active: 'bg-blue-100 text-blue-800',
      won: 'bg-green-100 text-green-800',
      lost: 'bg-red-100 text-red-800'
    };
    
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusStyles[status]}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  const totalActive = betHistory.filter(bet => bet.status === 'active').length;
  const totalWon = betHistory.filter(bet => bet.status === 'won').length;
  const totalLost = betHistory.filter(bet => bet.status === 'lost').length;

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-6xl mx-auto">
        <div className="bg-white rounded-lg shadow-md p-6">
          <h1 className="text-3xl font-bold text-gray-800 mb-6">My Bets</h1>

          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-blue-50 p-4 rounded-lg">
              <h3 className="font-semibold text-blue-800">Total Bets</h3>
              <p className="text-2xl font-bold text-blue-600">{betHistory.length}</p>
            </div>
            <div className="bg-yellow-50 p-4 rounded-lg">
              <h3 className="font-semibold text-yellow-800">Active</h3>
              <p className="text-2xl font-bold text-yellow-600">{totalActive}</p>
            </div>
            <div className="bg-green-50 p-4 rounded-lg">
              <h3 className="font-semibold text-green-800">Won</h3>
              <p className="text-2xl font-bold text-green-600">{totalWon}</p>
            </div>
            <div className="bg-red-50 p-4 rounded-lg">
              <h3 className="font-semibold text-red-800">Lost</h3>
              <p className="text-2xl font-bold text-red-600">{totalLost}</p>
            </div>
          </div>

          {/* Filter Tabs */}
          <div className="flex space-x-4 mb-6">
            {['all', 'active', 'settled'].map((filterOption) => (
              <button
                key={filterOption}
                onClick={() => setFilter(filterOption)}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  filter === filterOption
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {filterOption.charAt(0).toUpperCase() + filterOption.slice(1)}
              </button>
            ))}
          </div>

          {/* Bets List */}
          <div className="space-y-4">
            {filteredBets.length === 0 ? (
              <div className="text-center py-12">
                <div className="text-6xl mb-4">📊</div>
                <h2 className="text-xl font-semibold text-gray-600 mb-2">
                  No {filter === 'all' ? '' : filter} bets found
                </h2>
                <p className="text-gray-500">
                  {filter === 'all' 
                    ? "You haven't placed any bets yet. Head to the sports page to get started!"
                    : `You don't have any ${filter} bets at the moment.`
                  }
                </p>
              </div>
            ) : (
              filteredBets.map((bet) => (
                <div key={bet.id} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-2">
                        <h3 className="font-semibold text-gray-800">{bet.game}</h3>
                        {getStatusBadge(bet.status)}
                      </div>
                      <p className="text-sm text-gray-600 mb-1">
                        {bet.type}: {bet.selection}
                      </p>
                      <p className="text-sm text-gray-500">
                        Placed on {bet.placedAt}
                      </p>
                    </div>
                    <div className="text-right">
                      <div className="text-sm text-gray-600">
                        Bet: <span className="font-medium">${bet.amount}</span>
                      </div>
                      <div className="text-sm text-gray-600">
                        Odds: <span className="font-medium">{bet.odds}</span>
                      </div>
                      {bet.status === 'active' && (
                        <div className="text-sm text-green-600">
                          To win: <span className="font-medium">${bet.potentialWin}</span>
                        </div>
                      )}
                      {bet.status === 'won' && (
                        <div className="text-sm text-green-600 font-semibold">
                          Won: ${bet.result}
                        </div>
                      )}
                      {bet.status === 'lost' && (
                        <div className="text-sm text-red-600 font-semibold">
                          Lost: $0.00
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default BetsPage;
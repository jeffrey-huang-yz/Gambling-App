import React from 'react';

const HomePage = () => {
  return (
    <div className="p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold text-gray-800 mb-6">Welcome Home</h1>
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-2xl font-semibold text-gray-700 mb-4">Dashboard</h2>
          <p className="text-gray-600 mb-4">
            Welcome to your home dashboard. Here you can find an overview of your activities and quick access to important features.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-blue-50 p-4 rounded-lg">
              <h3 className="font-semibold text-blue-800">Quick Stats</h3>
              <p className="text-blue-600">View your latest performance metrics</p>
            </div>
            <div className="bg-green-50 p-4 rounded-lg">
              <h3 className="font-semibold text-green-800">Recent Activity</h3>
              <p className="text-green-600">Check your recent actions and updates</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
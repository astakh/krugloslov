import React from "react";

const HomePage: React.FC = () => {
  return (
    <div className="app-content py-8">
      <h1 className="text-2xl font-bold text-center mb-4">Круглослов</h1>
      <p className="text-center text-gray-600">
        Интервальное повторение английских слов в контексте
      </p>
      <div className="mt-8 p-6 bg-white rounded-xl shadow-sm border border-gray-100">
        <p className="text-gray-500 text-center">
          Здесь будет главный экран с прогрессом обучения
        </p>
      </div>
    </div>
  );
};

export default HomePage;

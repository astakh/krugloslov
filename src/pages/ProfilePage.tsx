import React from "react";

const ProfilePage: React.FC = () => {
  return (
    <div className="app-content py-8">
      <h1 className="text-2xl font-bold text-center mb-4">Профиль</h1>
      <div className="mt-8 p-6 bg-white rounded-xl shadow-sm border border-gray-100">
        <p className="text-gray-500 text-center">
          Настройки и статистика пользователя (будет реализован)
        </p>
      </div>
    </div>
  );
};

export default ProfilePage;

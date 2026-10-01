import React from 'react';

export default function KnowledgePage() {
  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4">Knowledge Bases</h1>
      <p className="text-gray-600 mb-8">Manage your organization's documents and vector knowledge for AURA.</p>
      
      <div className="bg-white shadow rounded p-6 max-w-xl">
        <h2 className="text-xl font-semibold mb-4">Create Knowledge Base</h2>
        <form className="flex flex-col gap-4">
          <input type="text" placeholder="Knowledge Base Name" className="border p-2 rounded" />
          <textarea placeholder="Description" className="border p-2 rounded"></textarea>
          <button type="button" className="bg-blue-600 text-white py-2 rounded hover:bg-blue-700">
            Create
          </button>
        </form>
      </div>

      <div className="mt-8">
        <h2 className="text-xl font-semibold mb-4">Your Knowledge Bases</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-gray-50 border p-4 rounded">
            <h3 className="font-bold">Main Company Knowledge</h3>
            <p className="text-sm text-gray-500 mb-2">General employee handbooks and policies.</p>
            <button className="text-blue-600 hover:underline">View Documents &rarr;</button>
          </div>
        </div>
      </div>
    </div>
  );
}

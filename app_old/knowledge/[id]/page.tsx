import React from 'react';

export default function KnowledgeBaseDetailsPage({ params }: { params: { id: string } }) {
  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-2">Knowledge Base Details</h1>
      <p className="text-gray-500 mb-8">ID: {params.id}</p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div>
          <div className="bg-white shadow rounded p-6 mb-8">
            <h2 className="text-xl font-semibold mb-4">Upload Document</h2>
            <form className="flex flex-col gap-4">
              <input type="file" className="border p-2 rounded" />
              <button type="button" className="bg-blue-600 text-white py-2 rounded hover:bg-blue-700">
                Upload & Process
              </button>
            </form>
          </div>

          <div className="bg-white shadow rounded p-6">
            <h2 className="text-xl font-semibold mb-4">Documents</h2>
            <ul className="divide-y">
              <li className="py-2 flex justify-between items-center">
                <span>employee_handbook.pdf</span>
                <span className="text-sm bg-green-100 text-green-800 px-2 py-1 rounded">READY</span>
              </li>
              <li className="py-2 flex justify-between items-center">
                <span>Q3_financials.docx</span>
                <span className="text-sm bg-yellow-100 text-yellow-800 px-2 py-1 rounded">PROCESSING</span>
              </li>
            </ul>
          </div>
        </div>

        <div>
          <div className="bg-gray-50 border rounded p-6 h-full">
            <h2 className="text-xl font-semibold mb-4">Test Knowledge Base</h2>
            <p className="text-sm text-gray-500 mb-4">Ask a question to see what AURA retrieves.</p>
            <form className="flex flex-col gap-4">
              <textarea placeholder="e.g., What is our remote work policy?" className="border p-2 rounded h-32"></textarea>
              <button type="button" className="bg-gray-800 text-white py-2 rounded hover:bg-gray-900">
                Ask AURA
              </button>
            </form>
            
            <div className="mt-8">
              <h3 className="font-semibold mb-2">Retrieval Results</h3>
              <div className="bg-white border rounded p-4 text-sm text-gray-600">
                No query executed yet.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

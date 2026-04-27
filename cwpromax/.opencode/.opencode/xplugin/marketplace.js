/**
 * OpenCode Marketplace Plugin
 * 
 * This plugin provides a marketplace GUI for browsing and installing
 * OpenCode skills and agents. It integrates with the marketplace backend
 * API hosted on Intel CAAS.
 */

const MARKETPLACE_URL = process.env.MARKETPLACE_URL || 'https://ocode-marketplace.apps.intel.com'

export default function marketplacePlugin({ project, client, tool }) {
  // Register the marketplace tool
  tool('marketplace', {
    description: 'Open the OpenCode Marketplace to browse, search, and install skills and agents',
    parameters: {
      action: {
        type: 'string',
        description: 'Action to perform: browse, search, install, uninstall, list-installed',
        enum: ['browse', 'search', 'install', 'uninstall', 'list-installed'],
        default: 'browse'
      },
      query: {
        type: 'string',
        description: 'Search query (for search action) or skill/agent name (for install/uninstall)'
      },
      type: {
        type: 'string',
        description: 'Filter by type',
        enum: ['all', 'skill', 'agent'],
        default: 'all'
      }
    },
    execute: async ({ action, query, type }) => {
      switch (action) {
        case 'browse':
          return {
            message: `Opening OpenCode Marketplace GUI...`,
            url: MARKETPLACE_URL,
            instructions: `
The marketplace is available at: ${MARKETPLACE_URL}

You can also use the following commands:
- marketplace search <query> - Search for skills/agents
- marketplace install <name> - Install a skill/agent
- marketplace uninstall <name> - Uninstall a skill/agent
- marketplace list-installed - List installed skills/agents
            `.trim()
          }
        
        case 'search':
          if (!query) {
            return { error: 'Please provide a search query' }
          }
          const searchResults = await searchMarketplace(query, type)
          return {
            message: `Found ${searchResults.length} results for "${query}"`,
            results: searchResults
          }
        
        case 'install':
          if (!query) {
            return { error: 'Please provide a skill/agent name to install' }
          }
          const installResult = await installItem(query, project.path)
          return installResult
        
        case 'uninstall':
          if (!query) {
            return { error: 'Please provide a skill/agent name to uninstall' }
          }
          const uninstallResult = await uninstallItem(query, project.path)
          return uninstallResult
        
        case 'list-installed':
          const installed = await listInstalled(project.path)
          return {
            message: `Found ${installed.length} installed items`,
            items: installed
          }
        
        default:
          return { error: `Unknown action: ${action}` }
      }
    }
  })
  
  return {
    name: 'marketplace',
    
    hooks: {
      // Hook into session start to check for updates
      'session.start.after': async () => {
        try {
          const updates = await checkForUpdates()
          if (updates.length > 0) {
            return {
              message: `${updates.length} skill/agent update(s) available. Use 'marketplace browse' to view.`
            }
          }
        } catch (e) {
          // Silently ignore update check failures
        }
      }
    }
  }
}

// Helper functions
async function searchMarketplace(query, type = 'all') {
  try {
    const params = new URLSearchParams({ q: query })
    if (type !== 'all') params.append('type', type)
    
    const response = await fetch(`${MARKETPLACE_URL}/api/skills/search?${params}`)
    const data = await response.json()
    return data.data || []
  } catch (error) {
    console.error('Search failed:', error)
    return []
  }
}

async function installItem(name, projectPath) {
  try {
    const response = await fetch(`${MARKETPLACE_URL}/api/skills/install`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, targetPath: projectPath })
    })
    const data = await response.json()
    
    if (data.success) {
      return {
        success: true,
        message: `Successfully installed ${name}`,
        path: data.path
      }
    } else {
      return {
        success: false,
        error: data.error || 'Installation failed'
      }
    }
  } catch (error) {
    return {
      success: false,
      error: error.message
    }
  }
}

async function uninstallItem(name, projectPath) {
  try {
    const response = await fetch(`${MARKETPLACE_URL}/api/skills/uninstall`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, targetPath: projectPath })
    })
    const data = await response.json()
    
    if (data.success) {
      return {
        success: true,
        message: `Successfully uninstalled ${name}`
      }
    } else {
      return {
        success: false,
        error: data.error || 'Uninstallation failed'
      }
    }
  } catch (error) {
    return {
      success: false,
      error: error.message
    }
  }
}

async function listInstalled(projectPath) {
  try {
    const response = await fetch(`${MARKETPLACE_URL}/api/skills/installed?path=${encodeURIComponent(projectPath)}`)
    const data = await response.json()
    return data.data || []
  } catch (error) {
    console.error('Failed to list installed:', error)
    return []
  }
}

async function checkForUpdates() {
  try {
    const response = await fetch(`${MARKETPLACE_URL}/api/skills/updates`)
    const data = await response.json()
    return data.updates || []
  } catch (error) {
    return []
  }
}

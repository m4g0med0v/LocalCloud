use std::collections::HashMap;

/// Simple in-memory file store
#[derive(Debug, Clone)]
pub struct FileStore {
    files: HashMap<String, FileRecord>,
}

#[derive(Debug, Clone)]
pub struct FileRecord {
    pub id: String,
    pub name: String,
    pub size_bytes: u64,
    pub mime_type: Option<String>,
}

impl FileStore {
    pub fn new() -> Self {
        Self {
            files: HashMap::new(),
        }
    }

    pub fn insert(&mut self, record: FileRecord) {
        self.files.insert(record.id.clone(), record);
    }

    pub fn get(&self, id: &str) -> Option<&FileRecord> {
        self.files.get(id)
    }

    pub fn list(&self) -> Vec<&FileRecord> {
        let mut records: Vec<&FileRecord> = self.files.values().collect();
        records.sort_by(|a, b| a.name.cmp(&b.name));
        records
    }

    pub fn remove(&mut self, id: &str) -> Option<FileRecord> {
        self.files.remove(id)
    }
}

impl Default for FileStore {
    fn default() -> Self {
        Self::new()
    }
}

fn fibonacci(n: u32) -> Vec<u64> {
    match n {
        0 => vec![],
        1 => vec![0],
        _ => {
            let mut seq = vec![0u64, 1];
            while seq.len() < n as usize {
                let last = seq[seq.len() - 1];
                let prev = seq[seq.len() - 2];
                seq.push(last + prev);
            }
            seq
        }
    }
}

fn main() {
    let mut store = FileStore::new();

    store.insert(FileRecord {
        id: "abc".to_string(),
        name: "report.pdf".to_string(),
        size_bytes: 1_048_576,
        mime_type: Some("application/pdf".to_string()),
    });

    for record in store.list() {
        println!("{}: {} ({} bytes)", record.id, record.name, record.size_bytes);
    }

    println!("Fibonacci(10): {:?}", fibonacci(10));
}

package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"time"
)

type HealthResponse struct {
	Status  string `json:"status"`
	Version string `json:"version"`
	Time    string `json:"time"`
}

type FileInfo struct {
	ID        string `json:"id"`
	Name      string `json:"name"`
	SizeBytes int64  `json:"size_bytes"`
	MimeType  string `json:"mime_type,omitempty"`
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(HealthResponse{
		Status:  "ok",
		Version: "1.0.0",
		Time:    time.Now().UTC().Format(time.RFC3339),
	})
}

func fileHandler(w http.ResponseWriter, r *http.Request) {
	id := r.URL.Query().Get("id")
	if id == "" {
		http.Error(w, "missing id", http.StatusBadRequest)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(FileInfo{
		ID:        id,
		Name:      "example.pdf",
		SizeBytes: 1_048_576,
		MimeType:  "application/pdf",
	})
}

func fibonacci(n int) []int {
	if n <= 0 {
		return nil
	}
	seq := make([]int, n)
	seq[0] = 0
	if n > 1 {
		seq[1] = 1
	}
	for i := 2; i < n; i++ {
		seq[i] = seq[i-1] + seq[i-2]
	}
	return seq
}

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/health", healthHandler)
	mux.HandleFunc("/files", fileHandler)

	fmt.Printf("LocalCloud listening on :%s\n", port)
	log.Fatal(http.ListenAndServe(":"+port, mux))
}
